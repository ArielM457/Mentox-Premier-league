from dataclasses import dataclass
from enum import StrEnum
from math import isfinite

from match_intelligence.domain.contracts import Position


class IdentityStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"


class IdentityEvidenceKind(StrEnum):
    MANUAL_CONFIRMATION = "manual_confirmation"
    VERIFIED_ROSTER_MAPPING = "verified_roster_mapping"


class VisualIdentityError(ValueError):
    """La observación o asociación no tiene evidencia de identidad suficiente."""


@dataclass(frozen=True, slots=True)
class VisualTrackObservation:
    observation_id: str
    match_id: str
    video_time_ms: int
    track_id: str
    detector_confidence: float
    team_id: str | None = None
    position: Position | None = None

    def __post_init__(self) -> None:
        required = {
            "observation_id": self.observation_id,
            "match_id": self.match_id,
            "track_id": self.track_id,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise VisualIdentityError(
                "Faltan identificadores de seguimiento: " + ", ".join(missing)
            )
        if self.video_time_ms < 0:
            raise VisualIdentityError("video_time_ms no puede ser negativo")
        if not isfinite(self.detector_confidence) or not 0 <= self.detector_confidence <= 1:
            raise VisualIdentityError("detector_confidence debe estar entre 0 y 1")
        if self.team_id is not None and not self.team_id.strip():
            raise VisualIdentityError("team_id no puede estar vacío")


@dataclass(frozen=True, slots=True)
class ConfirmedPlayerIdentity:
    match_id: str
    track_id: str
    player_id: str
    evidence_kind: IdentityEvidenceKind
    evidence_reference: str
    verified_by: str

    def __post_init__(self) -> None:
        required = {
            "match_id": self.match_id,
            "track_id": self.track_id,
            "player_id": self.player_id,
            "evidence_reference": self.evidence_reference,
            "verified_by": self.verified_by,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise VisualIdentityError(
                "Falta evidencia de identidad: " + ", ".join(missing)
            )


@dataclass(frozen=True, slots=True)
class ResolvedVisualIdentity:
    observation_id: str
    match_id: str
    video_time_ms: int
    track_id: str
    player_id: str | None
    identity_status: IdentityStatus
    detector_confidence: float
    identity_evidence_kind: IdentityEvidenceKind | None
    identity_evidence_reference: str | None


class PlayerIdentityResolver:
    """Asocia un track solo cuando recibe evidencia ajena al detector."""

    def __init__(self, known_player_ids: set[str] | frozenset[str]) -> None:
        if not known_player_ids or any(not player_id.strip() for player_id in known_player_ids):
            raise VisualIdentityError("La plantilla conocida no puede estar vacía")
        self._known_player_ids = frozenset(known_player_ids)

    def resolve(
        self,
        observation: VisualTrackObservation,
        confirmed_identity: ConfirmedPlayerIdentity | None = None,
    ) -> ResolvedVisualIdentity:
        if confirmed_identity is None:
            return ResolvedVisualIdentity(
                observation_id=observation.observation_id,
                match_id=observation.match_id,
                video_time_ms=observation.video_time_ms,
                track_id=observation.track_id,
                player_id=None,
                identity_status=IdentityStatus.UNCONFIRMED,
                detector_confidence=observation.detector_confidence,
                identity_evidence_kind=None,
                identity_evidence_reference=None,
            )

        if confirmed_identity.match_id != observation.match_id:
            raise VisualIdentityError("La asociación pertenece a otro partido")
        if confirmed_identity.track_id != observation.track_id:
            raise VisualIdentityError("La asociación pertenece a otro track_id")
        if confirmed_identity.player_id not in self._known_player_ids:
            raise VisualIdentityError("player_id no pertenece a la plantilla conocida")

        return ResolvedVisualIdentity(
            observation_id=observation.observation_id,
            match_id=observation.match_id,
            video_time_ms=observation.video_time_ms,
            track_id=observation.track_id,
            player_id=confirmed_identity.player_id,
            identity_status=IdentityStatus.CONFIRMED,
            detector_confidence=observation.detector_confidence,
            identity_evidence_kind=confirmed_identity.evidence_kind,
            identity_evidence_reference=confirmed_identity.evidence_reference,
        )
