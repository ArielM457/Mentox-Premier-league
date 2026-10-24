from dataclasses import dataclass
from enum import StrEnum
from math import hypot, isfinite


class CandidateFusionError(ValueError):
    """La observación o política candidata es inválida."""


class CandidateStatus(StrEnum):
    CANDIDATE = "candidate"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ImageBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        values = (self.x_min, self.y_min, self.x_max, self.y_max)
        if any(not isfinite(value) or not 0 <= value <= 1 for value in values):
            raise CandidateFusionError("Las coordenadas deben estar entre 0 y 1")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise CandidateFusionError("La caja debe tener área positiva")

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)

    def center_distance(self, other: "ImageBox") -> float:
        own_x, own_y = self.center
        other_x, other_y = other.center
        return hypot(own_x - other_x, own_y - other_y)


@dataclass(frozen=True, slots=True)
class SpatialDetection:
    prediction_id: str
    timestamp_ms: int
    label: str
    confidence: float
    bounding_box: ImageBox
    track_id: int | None

    def __post_init__(self) -> None:
        if not self.prediction_id.strip() or not self.label.strip():
            raise CandidateFusionError("La detección necesita identificador y clase")
        if self.timestamp_ms < 0:
            raise CandidateFusionError("timestamp_ms no puede ser negativo")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise CandidateFusionError("confidence debe estar entre 0 y 1")


@dataclass(frozen=True, slots=True)
class TemporalAction:
    prediction_id: str
    timestamp_ms: int
    label: str
    visual_team: str
    confidence: float

    def __post_init__(self) -> None:
        if not all((self.prediction_id.strip(), self.label.strip(), self.visual_team.strip())):
            raise CandidateFusionError("La acción necesita identificador, clase y equipo visual")
        if self.timestamp_ms < 0:
            raise CandidateFusionError("timestamp_ms no puede ser negativo")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise CandidateFusionError("confidence debe estar entre 0 y 1")


@dataclass(frozen=True, slots=True)
class CandidateFusionPolicy:
    temporal_tolerance_ms: int = 120
    image_distance_tolerance: float = 0.12
    ambiguity_margin: float = 0.01
    minimum_action_confidence: float = 0.10

    def __post_init__(self) -> None:
        if self.temporal_tolerance_ms < 0:
            raise CandidateFusionError("temporal_tolerance_ms no puede ser negativo")
        values = (
            self.image_distance_tolerance,
            self.ambiguity_margin,
            self.minimum_action_confidence,
        )
        if any(not isfinite(value) or value < 0 for value in values):
            raise CandidateFusionError("Las tolerancias deben ser finitas y no negativas")
        if self.image_distance_tolerance > 2**0.5:
            raise CandidateFusionError("image_distance_tolerance excede la diagonal")
        if self.minimum_action_confidence > 1:
            raise CandidateFusionError("minimum_action_confidence no puede superar 1")


@dataclass(frozen=True, slots=True)
class FusionCandidate:
    action: TemporalAction
    ball: SpatialDetection
    player: SpatialDetection
    source_prediction_ids: tuple[str, str, str]
    track_id: int
    player_id: None
    action_ball_delta_ms: int
    action_player_delta_ms: int
    image_center_distance: float
    confidence: float


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    status: CandidateStatus
    action: TemporalAction
    candidate: FusionCandidate | None
    reasons: tuple[str, ...]


class CandidateFusionService:
    """Propone asociaciones revisables sin convertirlas en MatchEvent."""

    def __init__(self, policy: CandidateFusionPolicy) -> None:
        self.policy = policy

    def evaluate(
        self,
        action: TemporalAction,
        detections: tuple[SpatialDetection, ...],
    ) -> CandidateDecision:
        if action.confidence < self.policy.minimum_action_confidence:
            return self._reject(
                CandidateStatus.INSUFFICIENT_EVIDENCE,
                action,
                "La confianza de la acción no alcanza el umbral",
            )

        balls = self._within_time(action, detections, {"ball"})
        if not balls:
            return self._reject(
                CandidateStatus.INSUFFICIENT_EVIDENCE,
                action,
                "No existe una detección de balón dentro de la ventana temporal",
            )
        ball = min(
            balls,
            key=lambda item: (abs(item.timestamp_ms - action.timestamp_ms), -item.confidence),
        )

        players = [
            item
            for item in self._within_time(action, detections, {"player", "goalkeeper"})
            if item.track_id is not None
        ]
        if not players:
            return self._reject(
                CandidateStatus.INSUFFICIENT_EVIDENCE,
                action,
                "No existe un jugador con track_id dentro de la ventana temporal",
            )

        best_by_track: dict[int, tuple[float, SpatialDetection]] = {}
        for item in players:
            assert item.track_id is not None
            ranked_item = (ball.bounding_box.center_distance(item.bounding_box), item)
            current = best_by_track.get(item.track_id)
            if current is None or (ranked_item[0], -item.confidence) < (
                current[0],
                -current[1].confidence,
            ):
                best_by_track[item.track_id] = ranked_item
        ranked = sorted(
            best_by_track.values(),
            key=lambda pair: (pair[0], -pair[1].confidence),
        )
        distance, player = ranked[0]
        if distance > self.policy.image_distance_tolerance:
            return self._reject(
                CandidateStatus.INSUFFICIENT_EVIDENCE,
                action,
                "El jugador más cercano supera la tolerancia espacial de imagen",
            )
        if len(ranked) > 1 and ranked[1][0] - distance <= self.policy.ambiguity_margin:
            return self._reject(
                CandidateStatus.AMBIGUOUS,
                action,
                "Dos jugadores son espacialmente indistinguibles con la política actual",
            )

        assert player.track_id is not None
        candidate = FusionCandidate(
            action=action,
            ball=ball,
            player=player,
            source_prediction_ids=(
                action.prediction_id,
                ball.prediction_id,
                player.prediction_id,
            ),
            track_id=player.track_id,
            player_id=None,
            action_ball_delta_ms=abs(ball.timestamp_ms - action.timestamp_ms),
            action_player_delta_ms=abs(player.timestamp_ms - action.timestamp_ms),
            image_center_distance=distance,
            confidence=min(action.confidence, ball.confidence, player.confidence),
        )
        return CandidateDecision(CandidateStatus.CANDIDATE, action, candidate, ())

    def _within_time(
        self,
        action: TemporalAction,
        detections: tuple[SpatialDetection, ...],
        labels: set[str],
    ) -> list[SpatialDetection]:
        return [
            item
            for item in detections
            if item.label in labels
            and abs(item.timestamp_ms - action.timestamp_ms)
            <= self.policy.temporal_tolerance_ms
        ]

    @staticmethod
    def _reject(
        status: CandidateStatus,
        action: TemporalAction,
        reason: str,
    ) -> CandidateDecision:
        return CandidateDecision(status, action, None, (reason,))


def suppress_competing_candidates(
    candidates: list[FusionCandidate], *, tolerance_ms: int = 250
) -> tuple[list[FusionCandidate], list[FusionCandidate]]:
    """Conserva la hipótesis más fuerte por track dentro de una misma acción."""
    accepted: list[FusionCandidate] = []
    suppressed: list[FusionCandidate] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item.action.confidence, item.confidence),
        reverse=True,
    ):
        conflicts = any(
            item.track_id == candidate.track_id
            and abs(item.action.timestamp_ms - candidate.action.timestamp_ms) <= tolerance_ms
            for item in accepted
        )
        (suppressed if conflicts else accepted).append(candidate)
    accepted.sort(key=lambda item: item.action.timestamp_ms)
    suppressed.sort(key=lambda item: item.action.timestamp_ms)
    return accepted, suppressed
