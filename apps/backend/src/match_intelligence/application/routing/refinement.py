"""Create small, task-specific requests from deterministic routing results."""

from __future__ import annotations

from .contracts import (
    AgentRequest,
    ControlSignal,
    MetricUpdate,
    PlayContext,
    RoutingDecision,
)
from match_intelligence.application.narrative.contracts import ViewerPreferences


TASK_BY_ROUTE = {
    "danger_immediate": "danger_simulation",
    "moment_candidate": "moment_selector",
    "dead_ball_context": "narrator",
    "recap": "recap",
}
TTL_BY_ROUTE = {
    "danger_immediate": 8_000,
    "moment_candidate": 120_000,
    "dead_ball_context": 15_000,
    "recap": 300_000,
}


class AgentRequestRefiner:
    def refine(
        self,
        decision: RoutingDecision,
        metrics: list[MetricUpdate],
        play_context: PlayContext,
        preferences: ViewerPreferences,
        *,
        period: int,
        clock_ms: int,
        control_signal: ControlSignal | None,
    ) -> AgentRequest | None:
        task = TASK_BY_ROUTE.get(decision.route)
        if task is None:
            return None
        relevant_sources = set(decision.source_event_ids)
        compact_metrics = [
            metric for metric in metrics if set(metric.source_event_ids) & relevant_sources
        ] if relevant_sources else []
        return AgentRequest(
            request_id=f"agent-request-{decision.decision_id}",
            match_id=decision.match_id,
            task=task,
            priority=decision.priority,
            period=period,
            clock_ms=clock_ms,
            ttl_ms=TTL_BY_ROUTE[decision.route],
            source_event_ids=decision.source_event_ids,
            metrics=compact_metrics,
            play_context=play_context,
            preferences=preferences,
            control_signal=control_signal,
        )
