"""VAEP: evaluación de viabilidad y conversión a acciones tipo SPADL.

VAEP (Decroos et al., 2019) estima cuánto cambia la probabilidad de marcar y
de recibir gol tras cada acción. socceraction (MIT) lo implementa sobre
acciones SPADL con clasificadores entrenados en muchos partidos. Con
``MatchEvent 1.0`` faltan campos que esos clasificadores usan y no hay datos
con licencia para entrenarlos, por lo que el modelo queda desactivado.

``to_spadl_actions`` muestra qué parte de nuestros eventos sería representable
para medir la brecha con datos y no con suposiciones.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from importlib.util import find_spec

from match_intelligence.application.analytics.value_models import (
    ValueModelName,
    ValueModelStatus,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

MISSING_FIELDS = (
    "bodypart (pie, cabeza, otro) para cada acción",
    "tipos SPADL sin equivalente: dribble, cross, clearance, foul, saques y acciones del portero",
    "conducciones (carry) entre acciones; VAEP las usa para el estado del juego",
    "clasificadores de marcar y conceder entrenados con datos con licencia y validados",
)

_SPADL_TYPES = {
    EventType.PASS: "pass",
    EventType.SHOT: "shot",
    EventType.TACKLE: "tackle",
    EventType.RECOVERY: "interception",
}


@dataclass(frozen=True, slots=True)
class SpadlAction:
    event_id: str
    team_id: str
    player_id: str | None
    period: int
    time_seconds: float
    type_name: str
    result_name: str
    bodypart_name: str
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float


@dataclass(frozen=True, slots=True)
class SpadlConversion:
    actions: tuple[SpadlAction, ...]
    unsupported_event_ids: tuple[str, ...]
    missing_position_event_ids: tuple[str, ...]

    @property
    def coverage(self) -> float:
        total = len(self.actions) + len(self.unsupported_event_ids) + len(self.missing_position_event_ids)
        return len(self.actions) / total if total else 0.0


def to_spadl_actions(frame: PitchFrame, events: Sequence[MatchEvent]) -> SpadlConversion:
    """Convierte lo representable; ``bodypart`` queda como ``unknown`` porque no existe."""
    actions: list[SpadlAction] = []
    unsupported: list[str] = []
    missing: list[str] = []
    for event in events:
        type_name = _SPADL_TYPES.get(event.type)
        if type_name is None:
            unsupported.append(event.event_id)
            continue
        start = frame.event_start(event)
        if start is None:
            missing.append(event.event_id)
            continue
        end = frame.event_end(event) or start
        actions.append(
            SpadlAction(
                event_id=event.event_id,
                team_id=event.team_id,
                player_id=event.player_id,
                period=event.period,
                time_seconds=event.clock_ms / 1000,
                type_name=type_name,
                result_name=_result(event),
                bodypart_name="unknown",
                start_x_m=start[0] * frame.length_m / 100,
                start_y_m=start[1] * frame.width_m / 100,
                end_x_m=end[0] * frame.length_m / 100,
                end_y_m=end[1] * frame.width_m / 100,
            )
        )
    return SpadlConversion(tuple(actions), tuple(unsupported), tuple(missing))


def _result(event: MatchEvent) -> str:
    if event.outcome in {EventOutcome.SUCCESS, EventOutcome.GOAL}:
        return "success"
    if event.outcome is EventOutcome.UNKNOWN:
        return "unknown"
    return "fail"


class VaepFeasibilityModel:
    """Siempre desactivado con ``MatchEvent 1.0``; explica por qué."""

    name = ValueModelName.VAEP

    def status(self) -> ValueModelStatus:
        reasons = list(MISSING_FIELDS)
        if find_spec("socceraction") is None:
            reasons.append("socceraction no está instalado (dependencia opcional)")
        return ValueModelStatus(name=self.name, enabled=False, reasons=tuple(reasons))

    def value(self, frame: PitchFrame, event: MatchEvent) -> float | None:
        return None
