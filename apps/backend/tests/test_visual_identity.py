import pytest

from match_intelligence.application.visual_identity import (
    ConfirmedPlayerIdentity,
    IdentityEvidenceKind,
    IdentityStatus,
    PlayerIdentityResolver,
    VisualIdentityError,
    VisualTrackObservation,
)
from match_intelligence.domain.contracts import Position


def observation(*, confidence: float = 0.99) -> VisualTrackObservation:
    return VisualTrackObservation(
        observation_id="obs-001",
        match_id="synthetic-acceptance-001",
        video_time_ms=7_000,
        track_id="track-42",
        detector_confidence=confidence,
        team_id="team-aurora",
        position=Position(x=25, y=40),
    )


def resolver() -> PlayerIdentityResolver:
    return PlayerIdentityResolver({"aurora-4", "aurora-8"})


def confirmed_identity(**changes: str) -> ConfirmedPlayerIdentity:
    values = {
        "match_id": "synthetic-acceptance-001",
        "track_id": "track-42",
        "player_id": "aurora-4",
        "evidence_reference": "manual-review-001",
        "verified_by": "data-reviewer",
    }
    values.update(changes)
    return ConfirmedPlayerIdentity(
        **values,
        evidence_kind=IdentityEvidenceKind.MANUAL_CONFIRMATION,
    )


def test_unconfirmed_detection_preserves_track_and_omits_player() -> None:
    result = resolver().resolve(observation())

    assert result.track_id == "track-42"
    assert result.player_id is None
    assert result.identity_status is IdentityStatus.UNCONFIRMED
    assert result.identity_evidence_kind is None
    assert result.identity_evidence_reference is None


@pytest.mark.parametrize("confidence", [0, 0.5, 0.999, 1])
def test_detector_confidence_never_confirms_nominal_identity(
    confidence: float,
) -> None:
    result = resolver().resolve(observation(confidence=confidence))

    assert result.detector_confidence == confidence
    assert result.player_id is None
    assert result.identity_status is IdentityStatus.UNCONFIRMED


def test_explicit_evidence_can_confirm_a_known_player() -> None:
    result = resolver().resolve(observation(), confirmed_identity())

    assert result.track_id == "track-42"
    assert result.player_id == "aurora-4"
    assert result.identity_status is IdentityStatus.CONFIRMED
    assert result.identity_evidence_kind is IdentityEvidenceKind.MANUAL_CONFIRMATION
    assert result.identity_evidence_reference == "manual-review-001"


def test_identity_from_another_track_is_rejected() -> None:
    with pytest.raises(VisualIdentityError, match="otro track_id"):
        resolver().resolve(
            observation(),
            confirmed_identity(track_id="track-other"),
        )


def test_identity_from_another_match_is_rejected() -> None:
    with pytest.raises(VisualIdentityError, match="otro partido"):
        resolver().resolve(
            observation(),
            confirmed_identity(match_id="synthetic-other"),
        )


def test_player_outside_the_known_roster_is_rejected() -> None:
    with pytest.raises(VisualIdentityError, match="plantilla conocida"):
        resolver().resolve(
            observation(),
            confirmed_identity(player_id="unknown-99"),
        )


def test_confirmation_requires_a_traceable_reference() -> None:
    with pytest.raises(VisualIdentityError, match="evidence_reference"):
        confirmed_identity(evidence_reference="")


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan")])
def test_detector_confidence_must_be_a_probability(confidence: float) -> None:
    with pytest.raises(VisualIdentityError, match="detector_confidence"):
        observation(confidence=confidence)
