from datetime import UTC, datetime

import pytest

from match_intelligence.adapters.sources.soccernet_gamestate import convert_gamestate_rows


NOW = datetime(2026, 10, 25, tzinfo=UTC)


def test_gamestate_rows_keep_attributes_without_inventing_identity() -> None:
    result = convert_gamestate_rows([
        {
            "detection_id": "7",
            "frame_index": 25,
            "track_id": 14,
            "role": "player",
            "team": "left",
            "jersey_number": 9,
            "bbox_ltwh": [100, 50, 20, 60],
            "bbox_pitch": {"x_bottom_middle": 0.0, "y_bottom_middle": 0.0},
            "bbox_confidence": 0.91,
            "role_confidence": 0.87,
            "jersey_confidence": 0.66,
        }
    ], match_id="messi-001", fps=25, period=1, pitch_length_m=105,
       pitch_width_m=68, team_by_side={"left": "team-a", "right": "team-b"},
       produced_at=NOW)

    assert result.ignored_rows == 0
    assert result.rows_without_pitch_position == 0
    assert len(result.observations) == 1
    payload = result.observations[0].payload
    assert payload["jersey_number"] == 9
    assert payload["player_id"] is None
    assert payload["identity_status"] == "unconfirmed"
    assert result.frames[0].video_time_ms == 1_000
    tracked = result.frames[0].objects[0]
    assert tracked.track_id == "trk-gs-14"
    assert tracked.team_id == "team-a"
    assert tracked.player_id is None
    assert tracked.x_m == 52.5
    assert tracked.y_m == 34.0


def test_gamestate_observation_survives_without_calibration() -> None:
    result = convert_gamestate_rows([
        {"detection_id": "8", "frame_index": 2, "track_id": 3,
         "role": "player", "team": "right", "bbox_pitch": None}
    ], match_id="messi-001", fps=10, period=1, pitch_length_m=105,
       pitch_width_m=68, produced_at=NOW)

    assert len(result.observations) == 1
    assert result.observations[0].payload["pitch_position_m"] is None
    assert result.frames == []
    assert result.rows_without_pitch_position == 1


def test_gamestate_rejects_invalid_runtime_configuration() -> None:
    with pytest.raises(ValueError, match="fps"):
        convert_gamestate_rows([], match_id="m", fps=0, period=1,
                               pitch_length_m=105, pitch_width_m=68)
