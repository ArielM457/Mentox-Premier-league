"""Hitos de jugador (``milestone@1``).

Un hito se emite una sola vez, en el evento exacto que alcanza el umbral. Solo
se cuentan eventos con ``player_id``: la identidad no se infiere.
"""

from collections.abc import Callable

from match_intelligence.domain.contracts import EventOutcome, EventType, MatchEvent

from .models import IndicatorComponent
from .signals import NO_DETECTION, Detection, DetectionContext, Signal, signal_from
from .pitch import PitchFrame
from .statistics import is_completed_pass, is_progressive_pass, metric, pass_distance_m

MILESTONE_RULE = "milestone@1"
RECORD_MIN_DISTANCE_M = 40.0
RECORD_MIN_IMPROVEMENT_M = 5.0
RECORD_MIN_COMPLETED_PASSES = 10

LIMIT_IDENTITY = "Solo cuenta eventos con player_id; las acciones sin identificar no suman."

Rule = Callable[[PitchFrame, MatchEvent], bool]

MILESTONE_THRESHOLDS: dict[str, tuple[int, ...]] = {
    "passes_completed": (10, 25, 50),
    "progressive_passes": (3, 5, 10),
    "recoveries": (3, 5, 8),
    "tackles_won": (3, 5),
    "shots_on_target": (3,),
    "goals": (2, 3),
}

_RULES: dict[str, Rule] = {
    "passes_completed": lambda _, e: is_completed_pass(e),
    "progressive_passes": lambda frame, e: bool(is_progressive_pass(frame, e)),
    "recoveries": lambda _, e: e.type is EventType.RECOVERY,
    "tackles_won": lambda _, e: e.type is EventType.TACKLE and e.outcome is EventOutcome.SUCCESS,
    "shots_on_target": lambda _, e: e.type is EventType.SHOT
    and e.outcome in {EventOutcome.GOAL, EventOutcome.SAVED},
    "goals": lambda _, e: e.type is EventType.SHOT and e.outcome is EventOutcome.GOAL,
}


class MilestoneDetector:
    rule = MILESTONE_RULE

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], list[str]] = {}
        self._record_m: float | None = None
        self._record_event_id: str | None = None
        self._completed_passes = 0

    def observe(self, context: DetectionContext) -> Detection:
        event = context.event
        signals: list[Signal] = []
        record = self._record(context)
        if record is not None:
            signals.append(record)
        if event.player_id is None:
            return Detection(signals=tuple(signals)) if signals else NO_DETECTION

        for key, thresholds in MILESTONE_THRESHOLDS.items():
            if not _RULES[key](context.frame, event):
                continue
            counted = self._counts.setdefault((event.player_id, key), [])
            counted.append(event.event_id)
            if len(counted) not in thresholds:
                continue
            rank = thresholds.index(len(counted)) + 1
            signals.append(
                signal_from(
                    context, "player_milestone", self.rule,
                    facts=[
                        metric(key, len(counted), counted, team_id=event.team_id, player_id=event.player_id),
                    ],
                    source_event_ids=counted, team_id=event.team_id, player_ids=[event.player_id],
                    evidence_limits=[LIMIT_IDENTITY], magnitude=3 * rank,
                    magnitude_detail=f"{key} = {len(counted)} (umbral {rank} de {len(thresholds)})",
                )
            )
        return Detection(signals=tuple(signals)) if signals else NO_DETECTION

    def _record(self, context: DetectionContext) -> Signal | None:
        event = context.event
        if not is_completed_pass(event):
            return None
        distance = pass_distance_m(context.frame, event)
        completed_before = self._completed_passes
        self._completed_passes += 1
        if distance is None:
            return None
        previous, previous_id = self._record_m, self._record_event_id
        if previous is not None and distance <= previous:
            return None
        self._record_m, self._record_event_id = distance, event.event_id
        if (
            event.player_id is None
            or completed_before < RECORD_MIN_COMPLETED_PASSES
            or distance < RECORD_MIN_DISTANCE_M
            or (previous is not None and distance - previous < RECORD_MIN_IMPROVEMENT_M)
        ):
            return None

        components = []
        if previous is not None and previous_id is not None:
            components.append(
                IndicatorComponent(key="previous_record_m", value=round(previous, 1),
                                   unit="meters", source_event_ids=[previous_id])
            )
        sources = [event.event_id] + ([previous_id] if previous_id else [])
        return signal_from(
            context, "player_milestone", self.rule,
            facts=[
                metric("match_longest_pass_m", round(distance, 1), [event.event_id],
                       team_id=event.team_id, player_id=event.player_id, components=components),
            ],
            source_event_ids=sources, team_id=event.team_id, player_ids=[event.player_id],
            evidence_limits=[LIMIT_IDENTITY], magnitude=5,
            magnitude_detail=f"nuevo pase más largo del partido: {distance:.1f} m",
        )
