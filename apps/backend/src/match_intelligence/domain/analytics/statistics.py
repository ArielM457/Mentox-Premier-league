"""Estadísticas básicas recalculables desde sus eventos de origen.

Cada función recibe eventos ya ordenados y devuelve ``MetricValue`` con la
lista exacta de eventos que forman la cifra. Un conteo sin eventos vale cero
porque se observó el flujo; una proporción sin denominador queda no
disponible.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

from . import catalog
from .models import IndicatorComponent, MetricValue
from .pitch import DEFENSIVE_THIRD_X, FINAL_THIRD_X, PitchFrame
from .state import SHOT_ON_TARGET_OUTCOMES, MatchState, wins_ball

PROGRESSIVE_MIN_GAIN_M = 10.0
HIGH_RECOVERY_MIN_X = 60.0
UNAVAILABLE_TRACKING = (
    "MatchEvent 1.0 no trae posiciones sucesivas con tiempo; no se calcula velocidad "
    "ni distancia recorrida"
)


@dataclass(frozen=True, slots=True)
class EventWindow:
    """Ventana ``(start, end]`` del reloj dentro de un único período."""

    period: int
    start_clock_ms: int
    end_clock_ms: int

    @classmethod
    def ending_at(cls, period: int, end_clock_ms: int, length_ms: int) -> "EventWindow":
        return cls(period=period, start_clock_ms=end_clock_ms - length_ms, end_clock_ms=end_clock_ms)

    @property
    def window_ms(self) -> int:
        return self.end_clock_ms - self.start_clock_ms

    @property
    def elapsed_ms(self) -> int:
        """Duración efectiva: la ventana no empieza antes del inicio del período."""
        return self.end_clock_ms - max(0, self.start_clock_ms)

    def contains(self, event: MatchEvent) -> bool:
        return (
            event.period == self.period
            and self.start_clock_ms < event.clock_ms <= self.end_clock_ms
        )

    def filter(self, events: Sequence[MatchEvent]) -> list[MatchEvent]:
        return [event for event in events if self.contains(event)]

    def metric_fields(self) -> dict[str, int]:
        return {
            "window_ms": self.window_ms,
            "period": self.period,
            "window_start_clock_ms": self.start_clock_ms,
            "window_end_clock_ms": self.end_clock_ms,
        }


def metric(
    key: str,
    value: int | float | None,
    source_event_ids: Sequence[str] = (),
    *,
    team_id: str | None = None,
    player_id: str | None = None,
    window: EventWindow | None = None,
    reason: str | None = None,
    components: Sequence[IndicatorComponent] = (),
    unit: str | None = None,
    formula_version: str | None = None,
) -> MetricValue:
    """Construye una cifra con la unidad, versión y origen del catálogo."""
    item = catalog.definition(key)
    fields: dict[str, object] = window.metric_fields() if window else {}
    return MetricValue(
        key=key,
        team_id=team_id,
        player_id=player_id,
        value=value,
        available=value is not None,
        unit=unit or item.unit,
        formula_version=formula_version or item.formula_version,
        source_event_ids=list(source_event_ids),
        origin=item.origin,
        unavailable_reason=None if value is not None else (reason or item.when_unavailable),
        components=list(components),
        **fields,
    )


Predicate = Callable[[MatchEvent], bool]


def _ids(events: Sequence[MatchEvent], predicate: Predicate) -> list[str]:
    return [event.event_id for event in events if predicate(event)]


def _is(event_type: EventType, *outcomes: EventOutcome) -> Predicate:
    def check(event: MatchEvent) -> bool:
        return event.type is event_type and (not outcomes or event.outcome in outcomes)

    return check


def is_completed_pass(event: MatchEvent) -> bool:
    return event.type is EventType.PASS and event.outcome is EventOutcome.SUCCESS


def is_progressive_pass(frame: PitchFrame, event: MatchEvent) -> bool | None:
    """``None`` cuando el pase no puede evaluarse por falta de datos."""
    if not is_completed_pass(event):
        return False
    gain = frame.forward_gain_m(event)
    end = frame.event_end(event)
    if gain is None or end is None:
        return None
    return gain >= PROGRESSIVE_MIN_GAIN_M and end[0] >= DEFENSIVE_THIRD_X


def is_final_third_entry(frame: PitchFrame, event: MatchEvent) -> bool | None:
    if not is_completed_pass(event):
        return False
    start = frame.event_start(event)
    end = frame.event_end(event)
    if start is None or end is None:
        return None
    return start[0] < FINAL_THIRD_X <= end[0]


def is_high_recovery(frame: PitchFrame, event: MatchEvent) -> bool | None:
    if not wins_ball(event):
        return False
    start = frame.event_start(event)
    if start is None:
        return None
    return start[0] >= HIGH_RECOVERY_MIN_X


def pass_distance_m(frame: PitchFrame, event: MatchEvent) -> float | None:
    if event.type is not EventType.PASS or event.start is None or event.end is None:
        return None
    return frame.distance_m(event.start, event.end)


def _spatial_count(
    key: str,
    frame: PitchFrame,
    events: Sequence[MatchEvent],
    rule: Callable[[PitchFrame, MatchEvent], bool | None],
    candidates: Predicate,
    **owner: object,
) -> MetricValue:
    """Cuenta una regla espacial y muestra cuántos eventos pudieron evaluarse."""
    evaluated = 0
    matched: list[str] = []
    for event in events:
        if not candidates(event):
            continue
        result = rule(frame, event)
        if result is None:
            continue
        evaluated += 1
        if result:
            matched.append(event.event_id)
    if evaluated == 0:
        return metric(key, None, **owner)
    component = IndicatorComponent(key="evaluated_events", value=evaluated, unit="count")
    return metric(key, len(matched), matched, components=[component], **owner)


def _pass_accuracy(events: Sequence[MatchEvent], **owner: object) -> MetricValue:
    known = [
        event for event in events
        if event.type is EventType.PASS
        and event.outcome in {EventOutcome.SUCCESS, EventOutcome.FAILURE}
    ]
    if not known:
        return metric("pass_accuracy", None, **owner)
    completed = sum(1 for event in known if event.outcome is EventOutcome.SUCCESS)
    return metric(
        "pass_accuracy",
        round(100 * completed / len(known), 1),
        [event.event_id for event in known],
        components=[
            IndicatorComponent(key="passes_completed", value=completed, unit="count"),
            IndicatorComponent(key="passes_with_known_outcome", value=len(known), unit="count"),
        ],
        **owner,
    )


def _pass_distances(
    frame: PitchFrame, events: Sequence[MatchEvent], **owner: object
) -> list[MetricValue]:
    measured = [
        (event, distance)
        for event in events
        if (distance := pass_distance_m(frame, event)) is not None
    ]
    completed = [(event, distance) for event, distance in measured if is_completed_pass(event)]
    average = (
        metric(
            "avg_pass_distance_m",
            round(sum(distance for _, distance in measured) / len(measured), 1),
            [event.event_id for event, _ in measured],
            **owner,
        )
        if measured
        else metric("avg_pass_distance_m", None, **owner)
    )
    if completed:
        longest_event, longest = max(completed, key=lambda item: item[1])
        longest_metric = metric(
            "longest_pass_m", round(longest, 1), [longest_event.event_id], **owner
        )
    else:
        longest_metric = metric("longest_pass_m", None, **owner)
    return [average, longest_metric]


def _counts(events: Sequence[MatchEvent], **owner: object) -> list[MetricValue]:
    rules: tuple[tuple[str, Predicate], ...] = (
        ("goals", _is(EventType.SHOT, EventOutcome.GOAL)),
        ("shots", _is(EventType.SHOT)),
        ("shots_on_target", lambda e: e.type is EventType.SHOT and e.outcome in SHOT_ON_TARGET_OUTCOMES),
        ("passes_attempted", _is(EventType.PASS)),
        ("passes_completed", is_completed_pass),
        ("recoveries", _is(EventType.RECOVERY)),
        ("tackles", _is(EventType.TACKLE)),
        ("tackles_won", _is(EventType.TACKLE, EventOutcome.SUCCESS)),
        ("pressures", _is(EventType.PRESSURE)),
    )
    results = []
    for key, predicate in rules:
        ids = _ids(events, predicate)
        results.append(metric(key, len(ids), ids, **owner))
    return results


def team_statistics(
    frame: PitchFrame,
    events: Sequence[MatchEvent],
    team_id: str,
    *,
    window: EventWindow | None = None,
) -> list[MetricValue]:
    scoped = window.filter(events) if window else list(events)
    own = [event for event in scoped if event.team_id == team_id]
    owner = {"team_id": team_id, "window": window}
    return [
        *_counts(own, **owner),
        _pass_accuracy(own, **owner),
        _spatial_count("progressive_passes", frame, own, is_progressive_pass, is_completed_pass, **owner),
        _spatial_count("final_third_entries", frame, own, is_final_third_entry, is_completed_pass, **owner),
        _spatial_count("high_recoveries", frame, own, is_high_recovery, wins_ball, **owner),
        *_pass_distances(frame, own, **owner),
    ]


def player_statistics(
    frame: PitchFrame, events: Sequence[MatchEvent], player_id: str
) -> list[MetricValue]:
    own = [event for event in events if event.player_id == player_id]
    if not own:
        return []
    owner = {"team_id": own[0].team_id, "player_id": player_id}
    return [
        metric("involvement", len(own), [event.event_id for event in own], **owner),
        *_counts(own, **owner),
        _pass_accuracy(own, **owner),
        _spatial_count("progressive_passes", frame, own, is_progressive_pass, is_completed_pass, **owner),
        *_pass_distances(frame, own, **owner),
        metric("distance_covered_m", None, reason=UNAVAILABLE_TRACKING, **owner),
    ]


def possession_statistics(state: MatchState) -> list[MetricValue]:
    """Cambios y cuota de posesión según ``possession@1``."""
    changes = state.possession_changes
    results = [metric("possession_changes", len(changes), [c.event_id for c in changes])]
    totals = {team_id: state.possession_ms(team_id) for team_id in state.team_ids}
    attributed = sum(total for total, _ in totals.values())
    for team_id in state.team_ids:
        won = [c.event_id for c in changes if c.to_team_id == team_id]
        results.append(metric("possession_won", len(won), won, team_id=team_id))
        total, sources = totals[team_id]
        if attributed == 0:
            results.append(metric("possession_share", None, team_id=team_id))
            continue
        results.append(
            metric(
                "possession_share",
                round(100 * total / attributed, 1),
                sources,
                team_id=team_id,
                components=[
                    IndicatorComponent(key="possession_ms", team_id=team_id, value=total, unit="ms"),
                    IndicatorComponent(key="attributed_ms", value=attributed, unit="ms"),
                ],
            )
        )
    return results


def unavailable_speed_metrics() -> list[MetricValue]:
    """RF-12: se declaran no disponibles en lugar de estimarse."""
    return [
        metric("ball_speed_kmh", None, reason=UNAVAILABLE_TRACKING),
        metric("shot_speed_kmh", None, reason=UNAVAILABLE_TRACKING),
    ]
