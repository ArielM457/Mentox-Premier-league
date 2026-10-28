import pytest
from dataclasses import replace

from match_intelligence.application.gamestate_analysis import (
    GameStateAnalysis,
    GameStateSettings,
    GameStateUnavailableError,
)
from match_intelligence.domain.contracts import MatchMetadata, Team, Player


class Publisher:
    def __init__(self) -> None:
        self.items = []

    async def publish_many(self, observations):
        self.items.extend(observations)
        return len(observations)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_disabled_gamestate_does_not_require_remote_service() -> None:
    settings = GameStateSettings(None, None, None, "synthetic-videos", None)
    assert settings.configured is False


def test_gamestate_rows_are_sampled_and_boxes_are_normalized() -> None:
    analysis = GameStateAnalysis(
        Publisher(),
        GameStateSettings("https://model", "key", "https://blob", "videos", "match.mp4"),
    )
    rows = (
        {"detection_id": "1", "frame_index": 0, "track_id": 7, "role": "player",
         "team": "left", "jersey_number": 9, "bbox_ltwh": [100, 50, 20, 60],
         "bbox_confidence": 0.9},
        {"detection_id": "2", "frame_index": 1, "track_id": 7, "role": "player",
         "bbox_ltwh": [101, 50, 20, 60], "bbox_confidence": 0.91},
        {"detection_id": "3", "frame_index": 25, "track_id": 7, "role": "player",
         "bbox_ltwh": [200, 100, 40, 80], "bbox_confidence": 0.92},
    )

    observations = analysis._observations(
        "match-1", rows, {"fps": 25, "width": 1000, "height": 500}
    )

    assert len(observations) == 2
    assert observations[0].kind == "game_state_detection"
    assert observations[0].timestamp_ms == 0
    assert observations[0].payload["bounding_box"] == pytest.approx([0.1, 0.1, 0.12, 0.22])
    assert observations[0].payload["jersey_number"] == 9
    assert observations[0].payload["player_id"] is None
    assert observations[1].timestamp_ms == 1000


def test_sampling_keeps_original_frame_timestamp_instead_of_bucket_time() -> None:
    analysis = GameStateAnalysis(
        Publisher(),
        GameStateSettings("https://model", "key", "https://blob", "videos", "match.mp4"),
    )
    observations = analysis._observations(
        "match-1",
        ({"detection_id": "1", "frame_index": 6, "track_id": 7,
          "role": "player", "bbox_ltwh": [0, 0, 10, 10]},),
        {"fps": 25, "width": 100, "height": 100},
    )

    assert observations[0].timestamp_ms == 240
    assert observations[0].payload["video_time_ms"] == 240


@pytest.mark.anyio
async def test_prepare_polls_async_api_and_publishes_observations(monkeypatch) -> None:
    publisher = Publisher()
    analysis = GameStateAnalysis(
        publisher,
        GameStateSettings("https://model", "key", "https://blob", "videos", "match.mp4"),
    )
    monkeypatch.setattr(analysis, "readiness", lambda: _async({"status": "ready", "device": "T4"}))
    monkeypatch.setattr(analysis, "_download_video", lambda: _async(b"video"))
    monkeypatch.setattr(analysis, "_create", lambda video: _async({
        "analysis_id": "abc", "video": {"fps": 25, "width": 100, "height": 100}
    }))
    monkeypatch.setattr(analysis, "_wait", lambda analysis_id: _async(None))
    monkeypatch.setattr(analysis, "_result", lambda analysis_id: _async(({
        "detection_id": "1", "frame_index": 0, "track_id": 4, "role": "player",
        "bbox_ltwh": [10, 10, 20, 30], "bbox_confidence": 0.8,
    },)))

    result = await analysis.prepare("match-1")

    assert result["status"] == "ready"
    assert result["observations_published"] == 1
    assert publisher.items[0].payload["match_id"] == "match-1"


async def _async(value):
    return value


def test_zero_and_float_track_ids_are_consistent_and_missing_tracks_stay_unknown() -> None:
    analysis = GameStateAnalysis(Publisher(), GameStateSettings(None, None, None, "videos", None))
    observations = analysis._observations("m", (
        {"frame_index": 0, "track_id": 0, "detection_id": "zero"},
        {"frame_index": 0, "track_id": 14.0, "detection_id": "float"},
        {"frame_index": 0, "track_id": None, "detection_id": "none"},
        {"frame_index": -1, "track_id": 7},
    ), {"fps": 25, "width": 100, "height": 100})
    assert {item.payload["track_id"] for item in observations} == {"trk-gs-0", "trk-gs-14", None}
    assert len(observations) == 3


@pytest.mark.anyio
async def test_retry_resumes_remote_analysis_instead_of_uploading_again(monkeypatch) -> None:
    analysis = GameStateAnalysis(Publisher(), GameStateSettings("https://model", "key", "https://blob", "v", "m.mp4"))
    monkeypatch.setattr(analysis, "readiness", lambda: _async({"status": "ready"}))
    monkeypatch.setattr(analysis, "_download_video", lambda: _async(b"mp4"))
    uploads = []

    async def create(video):
        uploads.append(video)
        return {"analysis_id": "existing", "video": {"fps": 25}}

    async def timeout(analysis_id):
        raise GameStateUnavailableError("Tiempo máximo")

    monkeypatch.setattr(analysis, "_create", create)
    monkeypatch.setattr(analysis, "_wait", timeout)
    with pytest.raises(GameStateUnavailableError):
        await analysis.prepare("m")
    assert analysis.status()["status"] == "failed"
    monkeypatch.setattr(analysis, "_wait", lambda analysis_id: _async(None))
    monkeypatch.setattr(analysis, "_result", lambda analysis_id: _async(()))
    result = await analysis.prepare("m")
    assert result["status"] == "ready"
    assert len(uploads) == 1
    assert analysis.status()["analysis_id"] == "existing"
    assert analysis.status()["error"] is None


@pytest.mark.anyio
async def test_names_require_verified_roster_and_explicit_team_mapping(monkeypatch) -> None:
    settings = GameStateSettings("https://model", "key", "https://blob", "v", "m.mp4")
    analysis = GameStateAnalysis(Publisher(), settings)
    metadata = MatchMetadata(
        schema_version="1.0", match_id="m", home_team=Team(team_id="h", name="H"),
        away_team=Team(team_id="a", name="A"),
        pitch_length_m=105, pitch_width_m=68,
        players=[Player(player_id="h9", team_id="h", name="Nine", shirt_number=9)],
    )
    analysis._cached_rows = tuple(
        {"frame_index": frame, "track_id": 14.0, "role": "player", "team": "left",
         "jersey_number": 9, "jersey_confidence": 0.9,
         "bbox_pitch": {"x_bottom_middle": 0, "y_bottom_middle": 0}}
        for frame in range(3)
    )
    analysis._video = {"fps": 25}
    monkeypatch.setattr(analysis, "readiness", lambda: _async({"status": "ready"}))
    await analysis.prepare("m", metadata)
    assert analysis.tracking_frames[0].objects[0].player_id is None
    assert analysis.tracking_frames[0].objects[0].team_id is None
    analysis.settings = replace(settings, roster_verified=True, team_by_side=(("left", "h"),))
    await analysis.prepare("m", metadata)
    assert analysis.tracking_frames[0].objects[0].player_id == "h9"
    assert analysis.metrics_until(0)[0]["tracking_evidence"]["frames"] == 1


@pytest.mark.anyio
async def test_configured_endpoint_with_missing_key_fails_visibly() -> None:
    analysis = GameStateAnalysis(Publisher(), GameStateSettings("https://model", None, None, "v", None))
    with pytest.raises(GameStateUnavailableError, match="incompleto"):
        await analysis.prepare("m")
    assert analysis.status()["status"] == "failed"
