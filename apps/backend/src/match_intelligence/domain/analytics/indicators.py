"""Indicadores propios del equipo: control, impulso y caos.

No son métricas oficiales. Cada valor es una escala 0-100 definida por este
proyecto, con versión, ventana, pesos y referencias visibles en
``components``. Los pesos y referencias se eligieron con escenarios
sintéticos y deben revisarse antes de compararlos con otras fuentes.
"""

from collections.abc import Sequence

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

from .models import IndicatorComponent, MetricValue
from .pitch import FINAL_THIRD_X, PitchFrame
from .signals import NO_DETECTION, Detection, DetectionContext, EventHistory, signal_from
from .state import SHOT_ON_TARGET_OUTCOMES, MatchState, is_goal
from .statistics import (
    EventWindow,
    is_completed_pass,
    is_final_third_entry,
    is_high_recovery,
    is_progressive_pass,
    metric,
)

CONTROL_RULE = "control@1"
MOMENTUM_RULE = "momentum@1"
CHAOS_RULE = "chaos@1"
CONTROL_SHIFT_RULE = "control_shift@1"
CHAOS_PHASE_RULE = "chaos_phase@1"

CONTROL_WINDOW_MS = 180_000
CONTROL_MIN_EVENTS = 8
CONTROL_WEIGHTS = (("possession_time", 0.4), ("completed_passes", 0.3), ("final_third_actions", 0.3))
CONTROL_SHIFT_MIN_LEAD = 60.0
CONTROL_SHIFT_MIN_SWING = 20.0

MOMENTUM_HALF_LIFE_MS = 120_000
MOMENTUM_HORIZON_MS = 5 * MOMENTUM_HALF_LIFE_MS
MOMENTUM_MIN_TOTAL = 0.5

CHAOS_WINDOW_MS = 180_000
CHAOS_MIN_ELAPSED_MS = 60_000
CHAOS_MIN_EVENTS = 6
CHAOS_COMPONENTS = (
    ("possession_changes_per_min", 0.5, 6.0),
    ("failed_pass_ratio", 0.25, 0.5),
    ("duels_per_min", 0.25, 5.0),
)
CHAOS_ENTER = 60.0
CHAOS_EXIT = 40.0

LIMIT_TEAM_SCALE = "Indicador propio del equipo ({rule}); no es una estadística oficial."


def _unavailable(team_ids: Sequence[str], window: EventWindow, reason: str) -> dict[str, MetricValue]:
    return {
        team_id: metric("control_index", None, team_id=team_id, window=window, reason=reason)
        for team_id in team_ids
    }


def control_index(
    frame: PitchFrame, state: MatchState, events: Sequence[MatchEvent], window: EventWindow
) -> dict[str, MetricValue]:
    """``control@1`` para ambos equipos en una ventana; suman 100."""
    team_ids = frame.team_ids
    if len(events) < CONTROL_MIN_EVENTS:
        return _unavailable(team_ids, window, f"Menos de {CONTROL_MIN_EVENTS} eventos en la ventana")

    raw: dict[str, dict[str, tuple[float, list[str]]]] = {name: {} for name, _ in CONTROL_WEIGHTS}
    for team_id in team_ids:
        possession, spells = state.possession_ms(
            team_id, period=window.period,
            start_clock_ms=window.start_clock_ms, end_clock_ms=window.end_clock_ms,
        )
        raw["possession_time"][team_id] = (possession, spells)
        completed = [e.event_id for e in events if e.team_id == team_id and is_completed_pass(e)]
        raw["completed_passes"][team_id] = (len(completed), completed)
        territory = []
        for event in events:
            if event.team_id != team_id:
                continue
            point = frame.event_start(event)
            if point is not None and point[0] >= FINAL_THIRD_X:
                territory.append(event.event_id)
        raw["final_third_actions"][team_id] = (len(territory), territory)

    available = [
        (name, weight) for name, weight in CONTROL_WEIGHTS
        if sum(value for value, _ in raw[name].values()) > 0
    ]
    if len(available) < 2:
        return _unavailable(team_ids, window, "Menos de 2 componentes con datos en la ventana")

    total_weight = sum(weight for _, weight in available)
    raw_values: dict[str, float] = {}
    components: dict[str, list[IndicatorComponent]] = {team_id: [] for team_id in team_ids}
    for team_id in team_ids:
        score = 0.0
        for name, weight in available:
            value, sources = raw[name][team_id]
            total = sum(item for item, _ in raw[name].values())
            share = value / total
            contribution = 100 * weight * share / total_weight
            score += contribution
            components[team_id].append(
                IndicatorComponent(
                    key=f"{name}_share", team_id=team_id, value=round(100 * share, 1),
                    unit="percent", weight=weight, contribution=round(contribution, 1),
                    source_event_ids=sources,
                )
            )
        raw_values[team_id] = score

    first, second = team_ids
    values = {first: round(raw_values[first], 1)}
    values[second] = round(100 - values[first], 1)
    return {
        team_id: metric(
            "control_index", values[team_id],
            sorted({sid for component in components[team_id] for sid in component.source_event_ids}),
            team_id=team_id, window=window, components=components[team_id],
        )
        for team_id in team_ids
    }


def _threat(frame: PitchFrame, event: MatchEvent) -> tuple[str, float] | None:
    if event.type is EventType.SHOT:
        weight = 2.0
        if event.outcome in SHOT_ON_TARGET_OUTCOMES:
            weight += 1.0
        if is_goal(event):
            weight += 1.0
        return "shots", weight
    if is_completed_pass(event):
        if is_final_third_entry(frame, event):
            return "final_third_entries", 1.0
        if is_progressive_pass(frame, event):
            return "progressive_passes", 0.5
        return None
    if is_high_recovery(frame, event):
        return "high_recoveries", 1.0
    return None


def momentum_index(
    frame: PitchFrame, history: EventHistory, period: int, at_clock_ms: int
) -> dict[str, MetricValue]:
    """``momentum@1``: cuota de amenaza reciente con decaimiento exponencial."""
    window = EventWindow.ending_at(period, at_clock_ms, MOMENTUM_HORIZON_MS)
    totals: dict[str, dict[str, float]] = {team_id: {} for team_id in frame.team_ids}
    sources: dict[str, dict[str, list[str]]] = {team_id: {} for team_id in frame.team_ids}
    for event in history.window(window):
        threat = _threat(frame, event)
        if threat is None or event.team_id not in totals:
            continue
        category, weight = threat
        decay = 0.5 ** ((at_clock_ms - event.clock_ms) / MOMENTUM_HALF_LIFE_MS)
        totals[event.team_id][category] = totals[event.team_id].get(category, 0.0) + weight * decay
        sources[event.team_id].setdefault(category, []).append(event.event_id)

    team_totals = {team_id: sum(values.values()) for team_id, values in totals.items()}
    overall = sum(team_totals.values())
    if overall < MOMENTUM_MIN_TOTAL:
        return {
            team_id: metric("momentum_index", None, team_id=team_id, window=window,
                            reason="Sin amenaza reciente suficiente para comparar")
            for team_id in frame.team_ids
        }
    first, second = frame.team_ids
    values = {first: round(100 * team_totals[first] / overall, 1)}
    values[second] = round(100 - values[first], 1)
    result = {}
    for team_id in frame.team_ids:
        components = [
            IndicatorComponent(
                key=category, team_id=team_id, value=round(value, 2), unit="weighted_threat",
                contribution=round(100 * value / overall, 1),
                source_event_ids=sources[team_id][category],
            )
            for category, value in sorted(totals[team_id].items())
        ]
        result[team_id] = metric(
            "momentum_index", values[team_id],
            [sid for component in components for sid in component.source_event_ids],
            team_id=team_id, window=window, components=components,
        )
    return result


def chaos_index(
    frame: PitchFrame, state: MatchState, events: Sequence[MatchEvent], window: EventWindow
) -> MetricValue:
    """``chaos@1``: frecuencia de cambios de posesión, pases fallidos y duelos."""
    if window.elapsed_ms < CHAOS_MIN_ELAPSED_MS:
        return metric("chaos_index", None, window=window, reason="La ventana todavía dura menos de 60 s")
    if len(events) < CHAOS_MIN_EVENTS:
        return metric("chaos_index", None, window=window,
                      reason=f"Menos de {CHAOS_MIN_EVENTS} eventos en la ventana")

    minutes = window.elapsed_ms / 60_000
    changes = [
        change.event_id for change in state.possession_changes
        if change.period == window.period
        and window.start_clock_ms < change.clock_ms <= window.end_clock_ms
    ]
    known_passes = [
        e for e in events
        if e.type is EventType.PASS and e.outcome in {EventOutcome.SUCCESS, EventOutcome.FAILURE}
    ]
    failed = [e.event_id for e in known_passes if e.outcome is EventOutcome.FAILURE]
    duels = [e.event_id for e in events if e.type in {EventType.TACKLE, EventType.RECOVERY}]

    measured: dict[str, tuple[float | None, list[str]]] = {
        "possession_changes_per_min": (len(changes) / minutes, changes),
        "failed_pass_ratio": (
            (len(failed) / len(known_passes), failed) if len(known_passes) >= 4 else (None, [])
        ),
        "duels_per_min": (len(duels) / minutes, duels),
    }
    components = []
    total_weight = sum(weight for name, weight, _ in CHAOS_COMPONENTS if measured[name][0] is not None)
    score = 0.0
    for name, weight, reference in CHAOS_COMPONENTS:
        value, sources = measured[name]
        if value is None:
            continue
        contribution = 100 * weight * min(1.0, value / reference) / total_weight
        score += contribution
        components.append(
            IndicatorComponent(
                key=name, value=round(value, 2),
                unit="ratio" if name == "failed_pass_ratio" else "per_minute",
                weight=weight, reference=reference, contribution=round(contribution, 1),
                source_event_ids=sources,
            )
        )
    return metric(
        "chaos_index", round(score, 1),
        sorted({sid for component in components for sid in component.source_event_ids}),
        window=window, components=components,
    )


class ControlShiftDetector:
    """``control_shift@1``: otro equipo pasa a liderar con ≥ 60 y gana ≥ 20 puntos entre ventanas."""

    rule = CONTROL_SHIFT_RULE

    def __init__(self) -> None:
        self._leader: dict[int, str] = {}

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        current = EventWindow.ending_at(event.period, event.clock_ms, CONTROL_WINDOW_MS)
        if current.start_clock_ms <= 0:
            return NO_DETECTION
        previous = EventWindow.ending_at(event.period, current.start_clock_ms, CONTROL_WINDOW_MS)
        now = control_index(context.frame, context.state, context.history.window(current), current)
        before = control_index(context.frame, context.state, context.history.window(previous), previous)

        leader = next(
            (team_id for team_id, item in now.items()
             if item.available and item.value >= CONTROL_SHIFT_MIN_LEAD),  # type: ignore[operator]
            None,
        )
        if leader is None or not before[leader].available:
            return NO_DETECTION
        swing = now[leader].value - before[leader].value  # type: ignore[operator]
        if before[leader].value >= 50 or swing < CONTROL_SHIFT_MIN_SWING:  # type: ignore[operator]
            return NO_DETECTION
        if self._leader.get(event.period) == leader:
            return NO_DETECTION
        self._leader[event.period] = leader

        return Detection(
            signals=(
                signal_from(
                    context, "control_shift", self.rule,
                    facts=[now[leader], before[leader]],
                    source_event_ids=now[leader].source_event_ids or [event.event_id],
                    team_id=leader,
                    evidence_limits=[
                        LIMIT_TEAM_SCALE.format(rule=CONTROL_RULE),
                        "Compara dos ventanas consecutivas de 3 minutos del mismo período.",
                    ],
                    magnitude=int((swing - CONTROL_SHIFT_MIN_SWING) / 2),
                    magnitude_detail=f"control {before[leader].value} → {now[leader].value}",
                ),
            )
        )


class ChaosPhaseDetector:
    """``chaos_phase@1``: el índice de caos entra en ≥ 60; se rearma al bajar de 40."""

    rule = CHAOS_PHASE_RULE

    def __init__(self) -> None:
        self._active = False

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        window = EventWindow.ending_at(event.period, event.clock_ms, CHAOS_WINDOW_MS)
        chaos = chaos_index(context.frame, context.state, context.history.window(window), window)
        if not chaos.available:
            return NO_DETECTION
        if chaos.value < CHAOS_EXIT:  # type: ignore[operator]
            self._active = False
            return NO_DETECTION
        if self._active or chaos.value < CHAOS_ENTER:  # type: ignore[operator]
            return NO_DETECTION
        self._active = True
        return Detection(
            signals=(
                signal_from(
                    context, "chaos_phase", self.rule,
                    facts=[chaos], source_event_ids=chaos.source_event_ids or [event.event_id],
                    team_id=None,
                    evidence_limits=[
                        LIMIT_TEAM_SCALE.format(rule=CHAOS_RULE),
                        "Las referencias de saturación se eligieron con escenarios sintéticos.",
                    ],
                    magnitude=int((chaos.value - CHAOS_ENTER) / 3),  # type: ignore[operator]
                    magnitude_detail=f"caos {chaos.value} en 3 minutos",
                ),
            )
        )
