import pytest

from match_intelligence.application.observation_fusion import (
    ActionObservation,
    FusionPolicy,
    FusionStatus,
    ObservationFusionError,
    ObservationFusionService,
)
from match_intelligence.application.visual_identity import (
    ConfirmedPlayerIdentity,
    IdentityEvidenceKind,
    IdentityStatus,
    PlayerIdentityResolver,
    VisualTrackObservation,
)
from match_intelligence.domain.contracts import (
    EventOutcome,
    EventSource,
    EventType,
    Position,
)


def action(**changes: object) -> ActionObservation:
    values: dict[str, object] = {
        "observation_id": "action-001",
        "match_id": "synthetic-acceptance-001",
        "period": 1,
        "clock_ms": 5_000,
        "video_time_ms": 7_000,
        "event_type": EventType.PASS,
        "outcome": EventOutcome.SUCCESS,
        "detector_confidence": 0.8,
        "track_id": "track-42",
        "team_id": "team-aurora",
        "position": Position(x=25, y=40),
    }
    values.update(changes)
    return ActionObservation(**values)  # type: ignore[arg-type]


def track(**changes: object) -> VisualTrackObservation:
    values: dict[str, object] = {
        "observation_id": "track-obs-001",
        "match_id": "synthetic-acceptance-001",
        "video_time_ms": 7_200,
        "track_id": "track-42",
        "detector_confidence": 0.9,
        "team_id": "team-aurora",
        "position": Position(x=26, y=40),
    }
    values.update(changes)
    return VisualTrackObservation(**values)  # type: ignore[arg-type]


def service() -> ObservationFusionService:
    return ObservationFusionService(
        FusionPolicy(temporal_tolerance_ms=500, spatial_tolerance=2)
    )


def test_compatible_observations_create_a_traceable_event() -> None:
    action_observation = action()
    track_observation = track()

    result = service().fuse(action_observation, track_observation)

    assert result.status is FusionStatus.FUSED
    assert result.fused is not None
    assert result.fused.action_observation is action_observation
    assert result.fused.track_observation is track_observation
    assert result.fused.source_observation_ids == ("action-001", "track-obs-001")
    assert result.fused.track_id == "track-42"
    assert result.fused.temporal_delta_ms == 200
    assert result.fused.spatial_distance == 1
    assert result.fused.event.source is EventSource.VIDEO_MODEL
    assert result.fused.event.confidence == 0.8
    assert result.fused.event.player_id is None


def test_fused_identifier_is_deterministic() -> None:
    first = service().fuse(action(), track())
    second = service().fuse(action(), track())

    assert first.fused is not None
    assert second.fused is not None
    assert first.fused.event.event_id == second.fused.event.event_id


def test_confirmed_identity_is_preserved_in_the_fused_event() -> None:
    track_observation = track()
    resolver = PlayerIdentityResolver({"aurora-4"})
    identity = resolver.resolve(
        track_observation,
        ConfirmedPlayerIdentity(
            match_id=track_observation.match_id,
            track_id=track_observation.track_id,
            player_id="aurora-4",
            evidence_kind=IdentityEvidenceKind.MANUAL_CONFIRMATION,
            evidence_reference="manual-review-001",
            verified_by="reviewer",
        ),
    )

    result = service().fuse(action(), track_observation, identity)

    assert result.fused is not None
    assert result.fused.event.player_id == "aurora-4"
    assert result.fused.resolved_identity is identity
    assert identity.identity_status is IdentityStatus.CONFIRMED


def test_unconfirmed_identity_does_not_invent_player_id() -> None:
    track_observation = track()
    identity = PlayerIdentityResolver({"aurora-4"}).resolve(track_observation)

    result = service().fuse(action(), track_observation, identity)

    assert result.fused is not None
    assert result.fused.event.player_id is None
    assert result.fused.track_id == identity.track_id


def test_temporal_distance_outside_policy_does_not_emit_event() -> None:
    result = service().fuse(action(), track(video_time_ms=7_501))

    assert result.status is FusionStatus.INSUFFICIENT_EVIDENCE
    assert result.fused is None
    assert "501 ms supera 500 ms" in result.reasons[0]
    assert result.action_observation.observation_id == "action-001"
    assert result.track_observation.observation_id == "track-obs-001"


def test_spatial_distance_outside_policy_does_not_emit_event() -> None:
    result = service().fuse(track=track(position=Position(x=30, y=40)), action=action())

    assert result.status is FusionStatus.INSUFFICIENT_EVIDENCE
    assert result.fused is None
    assert "distancia espacial" in result.reasons[0]


def test_missing_position_is_reported_as_insufficient_evidence() -> None:
    result = service().fuse(action(position=None), track())

    assert result.status is FusionStatus.INSUFFICIENT_EVIDENCE
    assert result.fused is None
    assert result.reasons == ("Falta posición para comprobar compatibilidad espacial",)


def test_missing_track_id_is_reported_as_insufficient_evidence() -> None:
    result = service().fuse(action(track_id=None), track())

    assert result.status is FusionStatus.INSUFFICIENT_EVIDENCE
    assert result.fused is None
    assert result.reasons == ("La acción no identifica un track_id",)


@pytest.mark.parametrize(
    ("changed_action", "changed_track", "expected"),
    [
        ({"match_id": "other-match"}, {}, "partidos distintos"),
        ({"track_id": "track-other"}, {}, "track_id distintos"),
        ({"team_id": "team-rio"}, {}, "equipos distintos"),
    ],
)
def test_contradiction_never_produces_a_false_fact(
    changed_action: dict[str, object],
    changed_track: dict[str, object],
    expected: str,
) -> None:
    result = service().fuse(action(**changed_action), track(**changed_track))

    assert result.status is FusionStatus.CONTRADICTION
    assert result.fused is None
    assert any(expected in reason for reason in result.reasons)


def test_identity_for_another_observation_is_a_contradiction() -> None:
    track_observation = track()
    identity = PlayerIdentityResolver({"aurora-4"}).resolve(track_observation)
    wrong_identity = identity.__class__(
        observation_id="track-obs-other",
        match_id=identity.match_id,
        video_time_ms=identity.video_time_ms,
        track_id=identity.track_id,
        player_id=identity.player_id,
        identity_status=identity.identity_status,
        detector_confidence=identity.detector_confidence,
        identity_evidence_kind=identity.identity_evidence_kind,
        identity_evidence_reference=identity.identity_evidence_reference,
    )

    result = service().fuse(action(), track_observation, wrong_identity)

    assert result.status is FusionStatus.CONTRADICTION
    assert result.fused is None
    assert "otra observación" in result.reasons[0]


@pytest.mark.parametrize(
    ("temporal", "spatial"),
    [(-1, 1), (1, -1), (1, float("nan"))],
)
def test_policy_rejects_invalid_tolerances(temporal: int, spatial: float) -> None:
    with pytest.raises(ObservationFusionError):
        FusionPolicy(temporal_tolerance_ms=temporal, spatial_tolerance=spatial)
