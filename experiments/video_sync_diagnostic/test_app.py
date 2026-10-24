import asyncio
from pathlib import Path
import sys

from httpx import ASGITransport, AsyncClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_sync_diagnostic.app import (  # noqa: E402
    VIDEO_PATH,
    app,
    index,
    video as video_response,
)


async def new_session(client: AsyncClient) -> dict[str, object]:
    response = await client.post("/api/integration/video-sync/session")
    assert response.status_code == 200
    return response.json()


def run_scenario(scenario) -> None:
    async def execute() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://diagnostic.test",
        ) as client:
            await scenario(client)

    asyncio.run(execute())


def test_session_uses_supplied_alignment_not_detection() -> None:
    async def scenario(client: AsyncClient) -> None:
        session = await new_session(client)
        assert session["timing_basis"] == "provided_event_timestamp"
        assert session["detection_status"] == "not_automatic_detection"
        assert session["visible_events"] == []

    run_scenario(scenario)


def test_page_and_permitted_video_are_served() -> None:
    if not VIDEO_PATH.is_file():
        pytest.skip("El MP4 local de DV-US-17 no está disponible")

    page = index()
    media = video_response()

    page_content = Path(page.path).read_text(encoding="utf-8")
    assert "Pipeline integrado" in page_content
    assert "Ventana alrededor del video" not in page_content
    assert "Observaciones recibidas desde Play" in page_content
    assert media.media_type == "video/mp4"
    assert Path(media.path).stat().st_size > 0


def test_page_uses_official_pipeline_api() -> None:
    async def scenario(client: AsyncClient) -> None:
        status = (await client.get("/api/v1/integration/status")).json()
        timeline = (
            await client.get(
                "/api/v1/integration/timeline",
                params={"start_ms": 19_400, "end_ms": 19_900},
            )
        ).json()

        assert status["status"] == "ready"
        assert status["fusion"]["match_events_published"] == 0
        assert len(timeline["fusion_candidates"]) == 1

    run_scenario(scenario)


def test_play_advance_and_pause_do_not_emit_future_events() -> None:
    async def scenario(client: AsyncClient) -> None:
        await new_session(client)
        await client.post("/api/integration/video-sync/play")
        advanced = (
            await client.post(
                "/api/integration/video-sync/advance",
                json={"video_time_ms": 6_000},
            )
        ).json()
        await client.post("/api/integration/video-sync/pause")
        paused = (
            await client.post(
                "/api/integration/video-sync/advance",
                json={"video_time_ms": 16_000},
            )
        ).json()

        assert [event["event_id"] for event in advanced["visible_events"]] == [
            "evt-pass-005"
        ]
        assert paused["video_time_ms"] == 6_000
        assert paused["event_cursor"] == 1

    run_scenario(scenario)


def test_seek_rebuilds_without_republishing_history() -> None:
    async def scenario(client: AsyncClient) -> None:
        await new_session(client)
        response = (
            await client.post(
                "/api/integration/video-sync/seek",
                json={"video_time_ms": 21_000},
            )
        ).json()
        assert response["visible_events"] == []
        assert response["reconstructed_state"]["event_count"] == 4
        assert response["event_cursor"] == 4

    run_scenario(scenario)


def test_backward_seek_and_restart_reconstruct_shorter_state() -> None:
    async def scenario(client: AsyncClient) -> None:
        await new_session(client)
        await client.post(
            "/api/integration/video-sync/seek",
            json={"video_time_ms": 26_000},
        )
        backward = (
            await client.post(
                "/api/integration/video-sync/seek",
                json={"video_time_ms": 11_000},
            )
        ).json()
        restarted = (
            await client.post("/api/integration/video-sync/restart")
        ).json()

        assert backward["reconstructed_state"]["event_count"] == 2
        assert backward["visible_events"] == []
        assert restarted["video_time_ms"] == 0
        assert restarted["event_cursor"] == 0
        assert restarted["playback_state"] == "paused"
        assert restarted["visible_events"] == []

    run_scenario(scenario)


def test_log_is_structured_and_contains_no_sensitive_data() -> None:
    async def scenario(client: AsyncClient) -> None:
        await new_session(client)
        await client.post("/api/integration/video-sync/play")
        log = (await client.get("/api/integration/video-sync/log")).json()
        assert log["experiment"] == "DV-US-18"
        assert log["contains_sensitive_data"] is False
        assert [record["action"] for record in log["records"]] == [
            "session_created",
            "play",
        ]

    run_scenario(scenario)
