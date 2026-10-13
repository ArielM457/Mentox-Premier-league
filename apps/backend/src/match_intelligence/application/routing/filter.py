"""Deterministic filter that keeps routine events away from language models."""

from __future__ import annotations

from collections import defaultdict

from .catalog import PlayCatalog
from .contracts import (
    MetricUpdate,
    PlayContext,
    RoutingDecision,
    RoutingEvaluationRequest,
    RoutingEvent,
)


METRIC_KEYS = {
    "pass": "passes",
    "shot": "shots",
    "tackle": "tackles",
    "possession_change": "possession_changes",
    "pressure": "pressures",
    "recovery": "recoveries",
}


class EventFilterService:
    def __init__(self, catalog: PlayCatalog | None = None) -> None:
        self.catalog = catalog or PlayCatalog()

    def evaluate(
        self, request: RoutingEvaluationRequest
    ) -> tuple[RoutingDecision, list[MetricUpdate], PlayContext, list[str], list[RoutingEvent]]:
        seen = set(request.existing_event_ids)
        accepted: list[RoutingEvent] = []
        ignored: list[str] = []
        for event in sorted(request.events, key=lambda item: (item.period, item.clock_ms, item.event_id)):
            if event.event_id in seen:
                ignored.append(event.event_id)
                continue
            seen.add(event.event_id)
            accepted.append(event)

        metrics = self._metrics(accepted)
        play_context = self.catalog.match(accepted)
        signal = request.control_signal
        source_ids = list(
            dict.fromkeys(
                source_id
                for event in accepted
                for source_id in [*event.related_event_ids, event.event_id]
            )
        )
        suffix = source_ids[-1] if source_ids else signal.type if signal else "empty"

        if signal and signal.type in {"period_ended", "match_ended"}:
            decision = self._decision(request.match_id, suffix, "recap", 100 if signal.type == "match_ended" else 85, [signal.type], source_ids)
        elif signal and signal.type == "play_stopped":
            decision = self._decision(request.match_id, suffix, "dead_ball_context", 50, ["play_stopped"], source_ids)
        elif accepted and self._is_immediate_danger(accepted[-1]):
            decision = self._decision(request.match_id, suffix, "danger_immediate", 95, ["dangerous_shot", *play_context.signals], source_ids)
        elif play_context.match_status == "confirmed":
            decision = self._decision(request.match_id, suffix, "moment_candidate", 70, [f"pattern:{play_context.pattern_key}"], source_ids)
        elif accepted:
            decision = self._decision(request.match_id, suffix, "metrics_only", 0, ["no_narrative_trigger"], source_ids)
        else:
            decision = self._decision(request.match_id, suffix, "rejected", 0, ["all_events_already_processed"], [])
        return decision, metrics, play_context, ignored, accepted

    @staticmethod
    def _is_immediate_danger(event: RoutingEvent) -> bool:
        return event.type == "shot" and (
            event.outcome == "goal" or (event.start is not None and event.start.x >= 75)
        )

    @staticmethod
    def _metrics(events: list[RoutingEvent]) -> list[MetricUpdate]:
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for event in events:
            grouped[(METRIC_KEYS[event.type], event.team_id)].append(event.event_id)
        return [
            MetricUpdate(key=key, team_id=team_id, value=len(sources), source_event_ids=sources)
            for (key, team_id), sources in sorted(grouped.items())
        ]

    @staticmethod
    def _decision(match_id: str, suffix: str, route: str, priority: int, reasons: list[str], sources: list[str]) -> RoutingDecision:
        return RoutingDecision(
            decision_id=f"route-{match_id}-{suffix}",
            match_id=match_id,
            route=route,
            priority=priority,
            reason_codes=list(dict.fromkeys(reasons)),
            source_event_ids=sources,
        )
