"""Agrupación de eventos en jugadas (``sequence@1``).

Una jugada es una serie de acciones de un mismo equipo con el balón:

1. Empieza con un evento que da la posesión (ver ``possession@1``).
2. Sigue mientras el mismo equipo realiza acciones con el balón y no pasan
   más de 20 s entre dos de ellas.
3. Termina con un tiro, cuando el rival gana el balón, con una pausa larga o
   al cambiar de período.
4. Las presiones y entradas fallidas del rival durante la jugada se guardan
   como contexto: no la cortan, pero quedan como evidencia.
"""

from dataclasses import dataclass, field, replace
from enum import StrEnum

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

from .pitch import PitchFrame
from .statistics import is_completed_pass
from .state import gains_possession

SEQUENCE_RULE_VERSION = "sequence@1"
MAX_GAP_MS = 20_000


class SequenceOutcome(StrEnum):
    GOAL = "goal"
    SHOT_SAVED = "shot_saved"
    SHOT_BLOCKED = "shot_blocked"
    SHOT_OFF_TARGET = "shot_off_target"
    SHOT = "shot"
    LOST = "lost"
    STOPPED = "stopped"
    PERIOD_END = "period_end"
    ONGOING = "ongoing"


_SHOT_OUTCOMES = {
    EventOutcome.GOAL: SequenceOutcome.GOAL,
    EventOutcome.SAVED: SequenceOutcome.SHOT_SAVED,
    EventOutcome.BLOCKED: SequenceOutcome.SHOT_BLOCKED,
    EventOutcome.OFF_TARGET: SequenceOutcome.SHOT_OFF_TARGET,
}

BALL_WINNING_STARTS = frozenset({"recovery", "tackle", "possession_change"})


@dataclass(frozen=True, slots=True)
class SequencePoint:
    """Posición normalizada que alcanza la jugada en un instante."""

    event_id: str
    clock_ms: int
    x: float


@dataclass(frozen=True, slots=True)
class PlaySequence:
    sequence_id: str
    match_id: str
    team_id: str
    period: int
    start_clock_ms: int
    end_clock_ms: int
    event_ids: tuple[str, ...]
    context_event_ids: tuple[str, ...]
    player_ids: tuple[str, ...]
    started_by: str
    outcome: SequenceOutcome
    pass_event_ids: tuple[str, ...]
    completed_pass_count: int
    points: tuple[SequencePoint, ...]
    closed_by_event_id: str | None = None

    @property
    def pass_count(self) -> int:
        return len(self.pass_event_ids)

    @property
    def duration_ms(self) -> int:
        return self.end_clock_ms - self.start_clock_ms

    @property
    def started_by_winning_ball(self) -> bool:
        return self.started_by in BALL_WINNING_STARTS

    @property
    def start_x(self) -> float | None:
        return self.points[0].x if self.points else None

    @property
    def max_x(self) -> float | None:
        return max(point.x for point in self.points) if self.points else None

    @property
    def end_x(self) -> float | None:
        return self.points[-1].x if self.points else None

    @property
    def progression(self) -> float | None:
        if not self.points:
            return None
        return self.max_x - self.start_x  # type: ignore[operator]

    @property
    def all_event_ids(self) -> tuple[str, ...]:
        return self.event_ids + self.context_event_ids


@dataclass(slots=True)
class _OpenSequence:
    first: MatchEvent
    events: list[MatchEvent] = field(default_factory=list)
    context: list[MatchEvent] = field(default_factory=list)
    points: list[SequencePoint] = field(default_factory=list)

    @property
    def team_id(self) -> str:
        return self.first.team_id

    @property
    def last(self) -> MatchEvent:
        return self.events[-1]


@dataclass(frozen=True, slots=True)
class SequenceUpdate:
    """Resultado de incorporar un evento: jugadas cerradas y jugada en curso."""

    closed: tuple[PlaySequence, ...]
    current: PlaySequence | None
    joined: PlaySequence | None = None


def _is_own_action(event: MatchEvent) -> bool:
    return gains_possession(event)


class SequenceBuilder:
    """Construye jugadas de forma incremental y causal."""

    def __init__(self, frame: PitchFrame) -> None:
        self._frame = frame
        self._open: _OpenSequence | None = None
        self._closed: list[PlaySequence] = []

    @property
    def closed(self) -> tuple[PlaySequence, ...]:
        return tuple(self._closed)

    @property
    def current(self) -> PlaySequence | None:
        if self._open is None:
            return None
        return self._freeze(self._open, SequenceOutcome.ONGOING)

    def add(self, event: MatchEvent) -> SequenceUpdate:
        closed: list[PlaySequence] = []
        joined: PlaySequence | None = None
        current = self._open

        if current is not None and current.last.period != event.period:
            closed.append(self._close(SequenceOutcome.PERIOD_END, None))
            current = None

        if not _is_own_action(event):
            if current is not None and event.team_id != current.team_id:
                current.context.append(event)
            return SequenceUpdate(tuple(closed), self.current)

        if current is not None:
            if event.team_id != current.team_id:
                closed.append(self._close(SequenceOutcome.LOST, event.event_id))
                current = None
            elif event.clock_ms - current.last.clock_ms > MAX_GAP_MS:
                closed.append(self._close(SequenceOutcome.STOPPED, event.event_id))
                current = None

        if current is None:
            current = _OpenSequence(first=event)
            self._open = current

        current.events.append(event)
        self._add_points(current, event)

        if event.type is EventType.SHOT:
            outcome = _SHOT_OUTCOMES.get(event.outcome, SequenceOutcome.SHOT)
            joined = self._close(outcome, None)
            closed.append(joined)
        else:
            joined = self._freeze(current, SequenceOutcome.ONGOING)

        return SequenceUpdate(tuple(closed), self.current, joined)

    def finish(self) -> tuple[PlaySequence, ...]:
        """Cierra la jugada abierta al terminar el flujo disponible."""
        if self._open is None:
            return ()
        return (self._close(SequenceOutcome.ONGOING, None),)

    def _add_points(self, sequence: _OpenSequence, event: MatchEvent) -> None:
        start = self._frame.event_start(event)
        if start is not None:
            sequence.points.append(SequencePoint(event.event_id, event.clock_ms, start[0]))
        if is_completed_pass(event):
            end = self._frame.event_end(event)
            if end is not None:
                sequence.points.append(SequencePoint(event.event_id, event.clock_ms, end[0]))

    def _close(self, outcome: SequenceOutcome, closed_by: str | None) -> PlaySequence:
        assert self._open is not None
        frozen = self._freeze(self._open, outcome)
        frozen = replace(frozen, closed_by_event_id=closed_by)
        self._closed.append(frozen)
        self._open = None
        return frozen

    @staticmethod
    def _freeze(sequence: _OpenSequence, outcome: SequenceOutcome) -> PlaySequence:
        players: list[str] = []
        for event in sequence.events:
            if event.player_id and event.player_id not in players:
                players.append(event.player_id)
        passes = [event for event in sequence.events if event.type is EventType.PASS]
        return PlaySequence(
            sequence_id=f"seq-{sequence.first.event_id}",
            match_id=sequence.first.match_id,
            team_id=sequence.team_id,
            period=sequence.first.period,
            start_clock_ms=sequence.first.clock_ms,
            end_clock_ms=sequence.last.clock_ms,
            event_ids=tuple(event.event_id for event in sequence.events),
            context_event_ids=tuple(event.event_id for event in sequence.context),
            player_ids=tuple(players),
            started_by=sequence.first.type.value,
            outcome=outcome,
            pass_event_ids=tuple(event.event_id for event in passes),
            completed_pass_count=sum(1 for event in passes if is_completed_pass(event)),
            points=tuple(sequence.points),
        )
