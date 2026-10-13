"""Señales detectadas por reglas y contexto común de los detectores.

Los detectores son causales: al observar un evento solo conocen los eventos
anteriores o simultáneos. Así un momento emitido durante la reproducción no
cambia cuando llegan eventos posteriores.
"""

from bisect import bisect_right
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from match_intelligence.domain.contracts import MatchEvent

from .models import MetricValue
from .pitch import PitchFrame
from .sequences import PlaySequence, SequenceUpdate
from .state import MatchState
from .statistics import EventWindow


class EventHistory:
    """Eventos ya observados, en orden, con búsqueda por ventana de reloj."""

    def __init__(self) -> None:
        self._events: list[MatchEvent] = []
        self._positions: dict[str, int] = {}
        self._clocks: dict[int, list[int]] = {}
        self._period_events: dict[int, list[MatchEvent]] = {}

    def append(self, event: MatchEvent) -> None:
        self._positions[event.event_id] = len(self._events)
        self._events.append(event)
        self._clocks.setdefault(event.period, []).append(event.clock_ms)
        self._period_events.setdefault(event.period, []).append(event)

    def __len__(self) -> int:
        return len(self._events)

    def __iter__(self) -> Iterator[MatchEvent]:
        return iter(self._events)

    @property
    def events(self) -> list[MatchEvent]:
        return self._events

    def position(self, event_id: str) -> int:
        return self._positions.get(event_id, len(self._events))

    def get(self, event_id: str) -> MatchEvent | None:
        position = self._positions.get(event_id)
        return None if position is None else self._events[position]

    def window(self, window: EventWindow) -> list[MatchEvent]:
        clocks = self._clocks.get(window.period)
        if not clocks:
            return []
        left = bisect_right(clocks, window.start_clock_ms)
        right = bisect_right(clocks, window.end_clock_ms)
        return self._period_events[window.period][left:right]


@dataclass(frozen=True, slots=True)
class Signal:
    kind: str
    rule_version: str
    anchor_event_id: str
    period: int
    clock_ms: int
    video_time_ms: int | None
    team_id: str | None
    player_ids: tuple[str, ...]
    facts: tuple[MetricValue, ...]
    source_event_ids: tuple[str, ...]
    evidence_limits: tuple[str, ...] = ()
    sequence_id: str | None = None
    magnitude: int = 0
    magnitude_detail: str = ""


@dataclass(frozen=True, slots=True)
class DetectionNote:
    """Regla que no pudo evaluarse o que se descartó por falta de evidencia."""

    rule: str
    anchor_event_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class DetectionContext:
    frame: PitchFrame
    event: MatchEvent
    history: EventHistory
    state: MatchState
    update: SequenceUpdate

    @property
    def sequence(self) -> PlaySequence | None:
        """Jugada a la que se sumó el evento, si es una acción con balón."""
        return self.update.joined


@dataclass(frozen=True, slots=True)
class Detection:
    signals: tuple[Signal, ...] = ()
    notes: tuple[DetectionNote, ...] = ()


NO_DETECTION = Detection()


class Detector(Protocol):
    rule: str

    def observe(self, context: DetectionContext) -> Detection: ...


def signal_from(
    context: DetectionContext,
    kind: str,
    rule_version: str,
    *,
    facts: Sequence[MetricValue],
    source_event_ids: Sequence[str],
    team_id: str | None,
    player_ids: Sequence[str] = (),
    evidence_limits: Sequence[str] = (),
    sequence_id: str | None = None,
    magnitude: int = 0,
    magnitude_detail: str = "",
) -> Signal:
    event = context.event
    ordered_sources = sorted(set(source_event_ids), key=context.history.position)
    return Signal(
        kind=kind,
        rule_version=rule_version,
        anchor_event_id=event.event_id,
        period=event.period,
        clock_ms=event.clock_ms,
        video_time_ms=event.video_time_ms,
        team_id=team_id,
        player_ids=tuple(dict.fromkeys(player_ids)),
        facts=tuple(facts),
        source_event_ids=tuple(ordered_sources),
        evidence_limits=tuple(evidence_limits),
        sequence_id=sequence_id,
        magnitude=max(0, min(15, magnitude)),
        magnitude_detail=magnitude_detail,
    )
