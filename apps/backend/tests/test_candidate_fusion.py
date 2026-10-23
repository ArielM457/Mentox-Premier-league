import pytest

from match_intelligence.application.candidate_fusion import (
    CandidateFusionError,
    CandidateFusionPolicy,
    CandidateFusionService,
    CandidateStatus,
    ImageBox,
    SpatialDetection,
    TemporalAction,
    suppress_competing_candidates,
)


def action(**changes: object) -> TemporalAction:
    values = dict(
        prediction_id="action-1",
        timestamp_ms=1_000,
        label="pass",
        visual_team="left",
        confidence=0.8,
    )
    values.update(changes)
    return TemporalAction(**values)  # type: ignore[arg-type]


def detection(label: str, track_id: int | None, **changes: object) -> SpatialDetection:
    values = dict(
        prediction_id=f"{label}-1",
        timestamp_ms=1_040,
        label=label,
        confidence=0.9,
        bounding_box=ImageBox(0.45, 0.45, 0.55, 0.55),
        track_id=track_id,
    )
    values.update(changes)
    return SpatialDetection(**values)  # type: ignore[arg-type]


def test_candidate_preserves_three_sources_and_never_invents_player() -> None:
    ball = detection("ball", 8)
    player = detection(
        "player", 42, prediction_id="player-1", bounding_box=ImageBox(0.50, 0.45, 0.60, 0.55)
    )

    result = CandidateFusionService(CandidateFusionPolicy()).evaluate(
        action(), (ball, player)
    )

    assert result.status is CandidateStatus.CANDIDATE
    assert result.candidate is not None
    assert result.candidate.source_prediction_ids == ("action-1", "ball-1", "player-1")
    assert result.candidate.track_id == 42
    assert result.candidate.player_id is None


def test_missing_ball_does_not_create_candidate() -> None:
    result = CandidateFusionService(CandidateFusionPolicy()).evaluate(
        action(), (detection("player", 42),)
    )

    assert result.status is CandidateStatus.INSUFFICIENT_EVIDENCE
    assert result.candidate is None


def test_close_players_are_reported_as_ambiguous() -> None:
    ball = detection("ball", 8)
    first = detection("player", 41, prediction_id="player-1")
    second = detection(
        "player", 42, prediction_id="player-2", bounding_box=ImageBox(0.451, 0.45, 0.551, 0.55)
    )

    result = CandidateFusionService(CandidateFusionPolicy()).evaluate(
        action(), (ball, first, second)
    )

    assert result.status is CandidateStatus.AMBIGUOUS
    assert result.candidate is None


def test_repeated_frames_of_same_track_do_not_create_false_ambiguity() -> None:
    ball = detection("ball", 8)
    first = detection("player", 42, prediction_id="player-frame-1")
    second = detection(
        "player",
        42,
        prediction_id="player-frame-2",
        timestamp_ms=1_080,
        bounding_box=ImageBox(0.451, 0.45, 0.551, 0.55),
    )

    result = CandidateFusionService(CandidateFusionPolicy()).evaluate(
        action(), (ball, first, second)
    )

    assert result.status is CandidateStatus.CANDIDATE
    assert result.candidate is not None
    assert result.candidate.track_id == 42


def test_low_confidence_action_is_not_fused() -> None:
    result = CandidateFusionService(CandidateFusionPolicy()).evaluate(
        action(confidence=0.09), (detection("ball", 8), detection("player", 42))
    )

    assert result.status is CandidateStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    "changes",
    [
        {"temporal_tolerance_ms": -1},
        {"image_distance_tolerance": -1},
        {"minimum_action_confidence": 1.1},
    ],
)
def test_invalid_policy_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(CandidateFusionError):
        CandidateFusionPolicy(**changes)  # type: ignore[arg-type]


def test_competing_actions_keep_only_strongest_hypothesis() -> None:
    service = CandidateFusionService(CandidateFusionPolicy())
    detections = (detection("ball", 8), detection("player", 42))
    weaker = service.evaluate(action(confidence=0.4), detections).candidate
    stronger = service.evaluate(
        action(prediction_id="action-2", timestamp_ms=1_160, confidence=0.8),
        detections,
    ).candidate
    assert weaker is not None and stronger is not None

    accepted, suppressed = suppress_competing_candidates([weaker, stronger])

    assert [item.action.prediction_id for item in accepted] == ["action-2"]
    assert [item.action.prediction_id for item in suppressed] == ["action-1"]
