from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from math import hypot, isfinite

from match_intelligence.application.visual_identity import (
    ResolvedVisualIdentity,
    VisualTrackObservation,
)
from match_intelligence.domain.contracts import (
    EventOutcome,
    EventSource,
    EventType,
    MatchEvent,
    Position,
)


class FusionStatus(StrEnum):
    FUSED = "fused"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONTRADICTION = "contradiction"


class ObservationFusionError(ValueError):
    """La entrada o política de fusión es inválida."""


@dataclass(frozen=True, slots=True)
class ActionObservation:
    observation_id: str
    match_id: str
    period: int
    clock_ms: int
    video_time_ms: int
    event_type: EventType
    outcome: EventOutcome
    detector_confidence: float
    track_id: str | None = None
    team_id: str | None = None
    position: Position | None = None

    def __post_init__(self) -> None:
        required = {
            "observation_id": self.observation_id,
            "match_id": self.match_id,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise ObservationFusionError(
                "Faltan identificadores de acción: " + ", ".join(missing)
            )
        if not 1 <= self.period <= 4:
            raise ObservationFusionError("period debe estar entre 1 y 4")
        if self.clock_ms < 0 or self.video_time_ms < 0:
            raise ObservationFusionError("Los tiempos no pueden ser negativos")
        if not isfinite(self.detector_confidence) or not 0 <= self.detector_confidence <= 1:
            raise ObservationFusionError("detector_confidence debe estar entre 0 y 1")
        for field_name, value in (
            ("track_id", self.track_id),
            ("team_id", self.team_id),
        ):
            if value is not None and not value.strip():
                raise ObservationFusionError(f"{field_name} no puede estar vacío")


@dataclass(frozen=True, slots=True)
class FusionPolicy:
    temporal_tolerance_ms: int
    spatial_tolerance: float

    def __post_init__(self) -> None:
        if self.temporal_tolerance_ms < 0:
            raise ObservationFusionError("temporal_tolerance_ms no puede ser negativo")
        if not isfinite(self.spatial_tolerance) or self.spatial_tolerance < 0:
            raise ObservationFusionError("spatial_tolerance debe ser finita y no negativa")


@dataclass(frozen=True, slots=True)
class FusedVideoEvent:
    event: MatchEvent
    source_observation_ids: tuple[str, str]
    track_id: str
    action_observation: ActionObservation
    track_observation: VisualTrackObservation
    resolved_identity: ResolvedVisualIdentity | None
    temporal_delta_ms: int
    spatial_distance: float


@dataclass(frozen=True, slots=True)
class FusionResult:
    status: FusionStatus
    fused: FusedVideoEvent | None
    reasons: tuple[str, ...]
    action_observation: ActionObservation
    track_observation: VisualTrackObservation
    resolved_identity: ResolvedVisualIdentity | None


class ObservationFusionService:
    """Fusiona solo observaciones compatibles y conserva todas las fuentes."""

    def __init__(self, policy: FusionPolicy) -> None:
        self._policy = policy

    @property
    def policy(self) -> FusionPolicy:
        return self._policy

    def fuse(
        self,
        action: ActionObservation,
        track: VisualTrackObservation,
        identity: ResolvedVisualIdentity | None = None,
    ) -> FusionResult:
        contradictions = self._contradictions(action, track, identity)
        if contradictions:
            return self._not_fused(
                FusionStatus.CONTRADICTION,
                contradictions,
                action,
                track,
                identity,
            )

        limitations: list[str] = []
        if action.track_id is None:
            limitations.append("La acción no identifica un track_id")
        if action.position is None or track.position is None:
            limitations.append("Falta posición para comprobar compatibilidad espacial")
        team_id = action.team_id or track.team_id
        if team_id is None:
            limitations.append("Falta team_id para construir MatchEvent")

        temporal_delta_ms = abs(action.video_time_ms - track.video_time_ms)
        if temporal_delta_ms > self._policy.temporal_tolerance_ms:
            limitations.append(
                f"La diferencia temporal {temporal_delta_ms} ms supera "
                f"{self._policy.temporal_tolerance_ms} ms"
            )

        spatial_distance: float | None = None
        if action.position is not None and track.position is not None:
            spatial_distance = hypot(
                action.position.x - track.position.x,
                action.position.y - track.position.y,
            )
            if spatial_distance > self._policy.spatial_tolerance:
                limitations.append(
                    f"La distancia espacial {spatial_distance:.3f} supera "
                    f"{self._policy.spatial_tolerance:.3f}"
                )

        if limitations:
            return self._not_fused(
                FusionStatus.INSUFFICIENT_EVIDENCE,
                limitations,
                action,
                track,
                identity,
            )

        assert action.track_id is not None
        assert action.position is not None
        assert spatial_distance is not None
        assert team_id is not None
        event = MatchEvent(
            schema_version="1.0",
            event_id=self._event_id(action, track),
            match_id=action.match_id,
            period=action.period,
            clock_ms=action.clock_ms,
            video_time_ms=action.video_time_ms,
            type=action.event_type,
            team_id=team_id,
            player_id=identity.player_id if identity is not None else None,
            start=action.position,
            end=None,
            outcome=action.outcome,
            source=EventSource.VIDEO_MODEL,
            confidence=min(action.detector_confidence, track.detector_confidence),
            related_event_ids=[],
        )
        fused = FusedVideoEvent(
            event=event,
            source_observation_ids=(action.observation_id, track.observation_id),
            track_id=action.track_id,
            action_observation=action,
            track_observation=track,
            resolved_identity=identity,
            temporal_delta_ms=temporal_delta_ms,
            spatial_distance=spatial_distance,
        )
        return FusionResult(
            status=FusionStatus.FUSED,
            fused=fused,
            reasons=(),
            action_observation=action,
            track_observation=track,
            resolved_identity=identity,
        )

    @staticmethod
    def _contradictions(
        action: ActionObservation,
        track: VisualTrackObservation,
        identity: ResolvedVisualIdentity | None,
    ) -> list[str]:
        reasons: list[str] = []
        if action.match_id != track.match_id:
            reasons.append("Las observaciones pertenecen a partidos distintos")
        if action.track_id is not None and action.track_id != track.track_id:
            reasons.append("Las observaciones tienen track_id distintos")
        if (
            action.team_id is not None
            and track.team_id is not None
            and action.team_id != track.team_id
        ):
            reasons.append("Las observaciones atribuyen equipos distintos")
        if identity is not None:
            if identity.observation_id != track.observation_id:
                reasons.append("La identidad corresponde a otra observación")
            if identity.match_id != track.match_id:
                reasons.append("La identidad corresponde a otro partido")
            if identity.track_id != track.track_id:
                reasons.append("La identidad corresponde a otro track_id")
        return reasons

    @staticmethod
    def _not_fused(
        status: FusionStatus,
        reasons: list[str],
        action: ActionObservation,
        track: VisualTrackObservation,
        identity: ResolvedVisualIdentity | None,
    ) -> FusionResult:
        return FusionResult(
            status=status,
            fused=None,
            reasons=tuple(reasons),
            action_observation=action,
            track_observation=track,
            resolved_identity=identity,
        )

    @staticmethod
    def _event_id(
        action: ActionObservation,
        track: VisualTrackObservation,
    ) -> str:
        source = (
            f"{action.match_id}:{action.observation_id}:{track.observation_id}"
        ).encode("utf-8")
        return f"video-{sha256(source).hexdigest()[:20]}"
