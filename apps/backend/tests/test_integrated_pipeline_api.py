import asyncio
import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from match_intelligence.main import app
from match_intelligence.application.integrated_pipeline import (
    IntegratedPipeline,
    PipelineArtifactError,
    PipelinePaths,
)
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_pipeline_rejects_fusion_generated_from_other_prediction_files(tmp_path: Path) -> None:
    roboflow_path = tmp_path / "roboflow.json"
    soccernet_path = tmp_path / "soccernet.json"
    fusion_path = tmp_path / "fusion.json"
    common_hash = "a" * 64
    roboflow_path.write_text(
        json.dumps(
            {
                "media_sha256": common_hash,
                "video": {"duration_ms": 1_000, "frames_processed": 1},
                "processing_time_ms": 1,
                "predictions": [],
            }
        ),
        encoding="utf-8",
    )
    soccernet_path.write_text(
        json.dumps(
            {
                "media_sha256": common_hash,
                "video": {"model_frames": 1},
                "processing_time_ms": 1,
                "predictions": [],
            }
        ),
        encoding="utf-8",
    )
    fusion_path.write_text(
        json.dumps(
            {
                "media_sha256": common_hash,
                "input_artifacts": {
                    "roboflow_sha256": "b" * 64,
                    "soccernet_sha256": "c" * 64,
                },
                "selected_result": {
                    "actions_evaluated": 0,
                    "candidates": 0,
                    "candidate_details": [],
                },
            }
        ),
        encoding="utf-8",
    )
    pipeline = IntegratedPipeline(
        PipelinePaths(
            roboflow=roboflow_path,
            soccernet=soccernet_path,
            fusion=fusion_path,
            video=tmp_path / "video.mp4",
        )
    )

    with pytest.raises(PipelineArtifactError, match="no corresponde"):
        pipeline.status()


def test_pipeline_status_and_timeline_expose_real_outputs_without_match_event() -> None:
    async def scenario() -> None:
        roboflow = json.loads(
            (
                REPOSITORY_ROOT
                / "experiments/roboflow-sports/output-real/roboflow-sports-predictions.json"
            ).read_text(encoding="utf-8")
        )
        soccernet = json.loads(
            (
                REPOSITORY_ROOT
                / "experiments/soccernet-teamspotting/output-real/soccernet-predictions.json"
            ).read_text(encoding="utf-8")
        )
        fusion = json.loads(
            (
                REPOSITORY_ROOT
                / "experiments/fusion-calibration/output/dv-us-21-report.json"
            ).read_text(encoding="utf-8")
        )
        selected = fusion["selected_result"]
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://backend.test",
        ) as client:
            status_response = await client.get("/api/v1/integration/status")
            timeline_response = await client.get(
                "/api/v1/integration/timeline",
                params={"start_ms": 19_400, "end_ms": 19_900},
            )

        assert status_response.status_code == 200
        status = status_response.json()
        assert status["status"] == "ready"
        assert status["roboflow"]["predictions"] == len(roboflow["predictions"])
        assert status["roboflow"]["predictions"] > 0
        assert status["soccernet"]["predictions"] == len(soccernet["predictions"])
        assert status["soccernet"]["predictions"] > 0
        assert status["fusion"] == {
            "status": "experimental_candidates_only",
            "actions_evaluated": selected["actions_evaluated"],
            "candidates": selected["candidates"],
            "match_events_published": 0,
        }

        assert timeline_response.status_code == 200
        timeline = timeline_response.json()
        expected_candidates = [
            item
            for item in selected["candidate_details"]
            if 19_400 <= item["action"]["timestamp_ms"] <= 19_900
        ]
        assert timeline["fusion_candidates"] == expected_candidates
        assert all(item["player_id"] is None for item in timeline["fusion_candidates"])

    asyncio.run(scenario())


def test_pipeline_rejects_inverted_window() -> None:
    async def scenario() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://backend.test",
        ) as client:
            response = await client.get(
                "/api/v1/integration/timeline",
                params={"start_ms": 500, "end_ms": 100},
            )
        assert response.status_code == 422
        assert response.json()["detail"] == "La ventana temporal es inválida"

    asyncio.run(scenario())


def test_live_worker_ingestion_is_deduplicated_and_observable() -> None:
    async def scenario() -> None:
        from match_intelligence.adapters.http.integration_router import live_hub

        live_hub.clear()
        item = {
            "observation_id": "live-001",
            "source": "roboflow",
            "kind": "spatial_detection",
            "timestamp_ms": 1200,
            "payload": {"label": "ball", "confidence": 0.8},
        }
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://backend.test"
        ) as client:
            first = await client.post("/api/v1/integration/live/observations", json=item)
            duplicate = await client.post("/api/v1/integration/live/observations", json=item)
            status = await client.get("/api/v1/integration/live/status")

        assert first.json() == {"accepted": True, "duplicate": False}
        assert duplicate.json() == {"accepted": False, "duplicate": True}
        assert status.json()["accepted"] == 1
        assert status.json()["duplicates"] == 1

    asyncio.run(scenario())


def test_playback_control_is_exposed_in_live_status() -> None:
    async def scenario() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://backend.test"
        ) as client:
            await client.post("/api/v1/integration/live/playback/restart")
            paused = await client.post(
                "/api/v1/integration/live/playback/advance",
                json={"video_time_ms": 1_000},
            )
            playing = await client.post(
                "/api/v1/integration/live/playback/play",
                json={"video_time_ms": 1_000},
            )
            status = await client.get("/api/v1/integration/live/status")

        assert paused.json()["position_ms"] == 0
        assert playing.json()["playback_state"] == "playing"
        assert status.json()["playback"]["position_ms"] == 1_000

    asyncio.run(scenario())
