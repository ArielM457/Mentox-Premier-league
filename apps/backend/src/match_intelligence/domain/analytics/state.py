"""Estado acumulado del partido: marcador, período, reloj y posesión.

El estado es un pliegue determinista sobre eventos ordenados por
``(period, clock_ms)``. Las reglas de posesión (``possession@1``) son:

1. ``pass``, ``shot``, ``recovery`` y ``possession_change`` dan la posesión al
   equipo del evento, con cualquier resultado.
2. Un ``tackle`` con resultado ``success`` también da la posesión al equipo
   que lo realiza. ``pressure`` y un ``tackle`` fallido no la cambian.
3. Un gol deja la posesión vacía hasta el siguiente evento que la otorgue
   (saque de centro desconocido).
4. Al empezar otro período la posesión queda vacía.
5. El tiempo de posesión se atribuye entre eventos del mismo período y nunca
   se extrapola más allá del último evento conocido.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

POSSESSION_RULE_VERSION = "possession@1"

POSSESSION_EVENT_TYPES = frozenset(
    {EventType.PASS, EventType.SHOT, EventType.RECOVERY, EventType.POSSESSION_CHANGE}
)
SHOT_ON_TARGET_OUTCOMES = frozenset({EventOutcome.GOAL, EventOutcome.SAVED})


def chronological(events: Iterable[MatchEvent]) -> list[MatchEvent]:
    """Orden deportivo ``(period, clock_ms)``; los empates conservan el orden de llegada."""
    return sorted(events, key=lambda event: (event.period, event.clock_ms))


def gains_possession(event: MatchEvent) -> bool:
    if event.type in POSSESSION_EVENT_TYPES:
        return True
    return event.type is EventType.TACKLE and event.outcome is EventOutcome.SUCCESS


def wins_ball(event: MatchEvent) -> bool:
    """Acción defensiva que termina con el balón para el equipo del evento."""
    if event.type in {EventType.RECOVERY, EventType.POSSESSION_CHANGE}:
        return True
    return event.type is EventType.TACKLE and event.outcome is EventOutcome.SUCCESS


def is_goal(event: MatchEvent) -> bool:
    return event.type is EventType.SHOT and event.outcome is EventOutcome.GOAL


@dataclass(frozen=True, slots=True)
class PossessionChange:
    event_id: str
    period: int
    clock_ms: int
    from_team_id: str
    to_team_id: str


@dataclass(slots=True)
class PossessionSpell:
    """Tramo continuo en que un equipo tiene el balón."""

    team_id: str
    period: int
    start_clock_ms: int
    end_clock_ms: int
    start_event_id: str
    event_ids: list[str] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        return self.end_clock_ms - self.start_clock_ms

    def overlap_ms(self, period: int, start_clock_ms: int, end_clock_ms: int) -> int:
        if period != self.period:
            return 0
        start = max(self.start_clock_ms, start_clock_ms)
        end = min(self.end_clock_ms, end_clock_ms)
        return max(0, end - start)


@dataclass(slots=True)
class MatchState:
    match_id: str
    team_ids: tuple[str, str]
    period: int = 1
    clock_ms: int = 0
    video_time_ms: int | None = None
    score: dict[str, int] = field(default_factory=dict)
    goal_event_ids: dict[str, list[str]] = field(default_factory=dict)
    possession_team_id: str | None = None
    possession_changes: list[PossessionChange] = field(default_factory=list)
    spells: list[PossessionSpell] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    last_event_id: str | None = None

    def __post_init__(self) -> None:
        for team_id in self.team_ids:
            self.score.setdefault(team_id, 0)
            self.goal_event_ids.setdefault(team_id, [])

    @classmethod
    def fold(
        cls, match_id: str, team_ids: tuple[str, str], events: Iterable[MatchEvent]
    ) -> "MatchState":
        state = cls(match_id=match_id, team_ids=team_ids)
        for event in events:
            state.apply(event)
        return state

    @property
    def current_spell(self) -> PossessionSpell | None:
        if self.possession_team_id is None or not self.spells:
            return None
        return self.spells[-1]

    def apply(self, event: MatchEvent) -> None:
        """Incorpora un evento posterior o igual al último aplicado."""
        if self.event_ids and event.period != self.period:
            # Un período nuevo cierra la posesión del anterior.
            self.possession_team_id = None

        spell = self.current_spell
        if spell is not None:
            spell.end_clock_ms = event.clock_ms

        if gains_possession(event) and event.team_id != self.possession_team_id:
            if self.possession_team_id is not None:
                self.possession_changes.append(
                    PossessionChange(
                        event_id=event.event_id,
                        period=event.period,
                        clock_ms=event.clock_ms,
                        from_team_id=self.possession_team_id,
                        to_team_id=event.team_id,
                    )
                )
            self.possession_team_id = event.team_id
            self.spells.append(
                PossessionSpell(
                    team_id=event.team_id,
                    period=event.period,
                    start_clock_ms=event.clock_ms,
                    end_clock_ms=event.clock_ms,
                    start_event_id=event.event_id,
                )
            )

        spell = self.current_spell
        if spell is not None and spell.team_id == event.team_id:
            spell.event_ids.append(event.event_id)

        if is_goal(event):
            self.score[event.team_id] = self.score.get(event.team_id, 0) + 1
            self.goal_event_ids.setdefault(event.team_id, []).append(event.event_id)
            self.possession_team_id = None

        self.period = event.period
        self.clock_ms = event.clock_ms
        self.video_time_ms = event.video_time_ms
        self.event_ids.append(event.event_id)
        self.last_event_id = event.event_id

    def possession_ms(
        self, team_id: str, *, period: int | None = None,
        start_clock_ms: int | None = None, end_clock_ms: int | None = None,
    ) -> tuple[int, list[str]]:
        """Milisegundos de posesión y eventos que abrieron cada tramo contado."""
        total = 0
        sources: list[str] = []
        if period is None:
            for spell in self.spells:
                if spell.team_id == team_id and spell.duration_ms > 0:
                    total += spell.duration_ms
                    sources.append(spell.start_event_id)
            return total, sources

        start = -1 if start_clock_ms is None else start_clock_ms
        # Los tramos son cronológicos: se recorren desde el final hasta salir de la ventana.
        for spell in reversed(self.spells):
            if spell.period < period or (spell.period == period and spell.end_clock_ms <= start):
                break
            if spell.team_id != team_id:
                continue
            end = spell.end_clock_ms if end_clock_ms is None else end_clock_ms
            duration = spell.overlap_ms(period, start, end)
            if duration > 0:
                total += duration
                sources.append(spell.start_event_id)
        sources.reverse()
        return total, sources
