from datetime import UTC, datetime

import pytest

from match_intelligence.adapters.sources.soccernet_gamestate import (
    convert_gamestate_rows,
    resolve_gamestate_identities,
)
from match_intelligence.domain.contracts import MatchMetadata, Player, Team


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


def test_identity_requires_repeated_roster_backed_jersey_votes() -> None:
    metadata = MatchMetadata(
        schema_version="1.0",
        match_id="messi-001",
        home_team=Team(team_id="home", name="Home"),
        away_team=Team(team_id="away", name="Away"),
        pitch_length_m=105,
        pitch_width_m=68,
        players=[
            Player(player_id="home-9", team_id="home", name="Nueve", shirt_number=9),
            Player(player_id="away-9", team_id="away", name="Nueve rival", shirt_number=9),
        ],
    )
    rows = [
        {"frame_index": frame, "track_id": 14, "team": "left", "jersey_number": jersey,
         "jersey_confidence": confidence}
        for frame, jersey, confidence in (
            (1, 9, 0.90), (2, 9, 0.85), (3, 9, 0.80), (4, 8, 0.55)
        )
    ]

    identities = resolve_gamestate_identities(
        rows,
        metadata=metadata,
        team_by_side={"left": "home", "right": "away"},
    )

    assert identities.player_by_track == {"trk-gs-14": "home-9"}
    assert identities.evidence_by_track["trk-gs-14"]["votes"] == 3
    assert identities.evidence_by_track["trk-gs-14"]["status"] == "confirmed"

    converted = convert_gamestate_rows(
        [{
            "detection_id": "7", "frame_index": 5, "track_id": 14, "role": "player",
            "team": "left", "jersey_number": 9,
            "bbox_pitch": {"x_bottom_middle": 0, "y_bottom_middle": 0},
        }],
        match_id="messi-001", fps=25, period=1, pitch_length_m=105, pitch_width_m=68,
        team_by_side={"left": "home"}, player_by_track=identities.player_by_track,
        identity_evidence_by_track=identities.evidence_by_track, produced_at=NOW,
    )
    assert converted.frames[0].objects[0].player_id == "home-9"
    assert converted.observations[0].payload["identity_status"] == "confirmed"


def test_duplicate_rows_do_not_count_as_independent_identity_votes() -> None:
    metadata = MatchMetadata(
        schema_version="1.0", match_id="m", home_team=Team(team_id="h", name="H"),
        away_team=Team(team_id="a", name="A"),
        pitch_length_m=105, pitch_width_m=68,
        players=[Player(player_id="h9", team_id="h", name="Nine", shirt_number=9)],
    )
    row = {"frame_index": 0, "track_id": 0, "team": "left", "jersey_number": 9,
           "jersey_confidence": 0.9}
    result = resolve_gamestate_identities([row] * 4, metadata=metadata, team_by_side={"left": "h"})
    assert result.player_by_track == {}
    assert result.evidence_by_track["trk-gs-0"]["votes"] == 1


def test_duplicate_tracks_and_nonfinite_fps_are_rejected() -> None:
    row = {"frame_index": 0, "track_id": 0, "role": "player",
           "bbox_pitch": {"x_bottom_middle": 0, "y_bottom_middle": 0}}
    result = convert_gamestate_rows([row, row], match_id="m", fps=25, period=1,
                                   pitch_length_m=105, pitch_width_m=68)
    assert len(result.frames[0].objects) == 1
    with pytest.raises(ValueError, match="fps"):
        convert_gamestate_rows([row], match_id="m", fps=float("nan"), period=1,
                               pitch_length_m=105, pitch_width_m=68)


def test_two_simultaneous_tracks_cannot_claim_the_same_player() -> None:
    metadata = MatchMetadata(
        schema_version="1.0", match_id="m", home_team=Team(team_id="h", name="H"),
        away_team=Team(team_id="a", name="A"), pitch_length_m=105, pitch_width_m=68,
        players=[Player(player_id="h9", team_id="h", name="Nine", shirt_number=9)],
    )
    rows = [
        {"frame_index": frame, "track_id": track, "team": "left", "jersey_number": 9,
         "jersey_confidence": 0.9}
        for track in (1, 2) for frame in range(3)
    ]
    identities = resolve_gamestate_identities(rows, metadata=metadata, team_by_side={"left": "h"})
    assert identities.player_by_track == {}
    assert identities.ambiguous_tracks == 2
