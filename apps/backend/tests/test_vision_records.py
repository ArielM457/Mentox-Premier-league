import pytest
from pydantic import ValidationError

from match_intelligence.domain.vision import BoundingBox, RoboflowDetectionRecord, SoccerNetActionRecord


def test_video_records_keep_detection_and_processing_evidence() -> None:
    action = SoccerNetActionRecord(
        observation_id="action-1", match_id="match-1", frame_index=25, period=1,
        clock_ms=1_000, video_time_ms=1_000, event_type="pass",
        possession_team_id="team-a", shirt_color_label="blue", confidence=0.91,
    )
    detection = RoboflowDetectionRecord(
        detection_id="det-1", match_id="match-1", frame_index=25, video_time_ms=1_000,
        class_name="player", confidence=0.88,
        bounding_box=BoundingBox(x=10, y=20, width=30, height=60),
        track_id="track-7", processing_latency_ms=42,
    )
    assert action.frame_index == detection.frame_index
    assert detection.processing_latency_ms == 42


def test_video_records_reject_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        SoccerNetActionRecord(
            observation_id="action-1", match_id="match-1", frame_index=0, period=1,
            clock_ms=0, video_time_ms=0, event_type="shot", confidence=1.2,
        )
