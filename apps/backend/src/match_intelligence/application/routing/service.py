"""One application entry point for filter, refinement and dispatch."""

from __future__ import annotations

from .contracts import PlayContext, RoutingEvaluationRequest, RoutingOutcome
from .filter import EventFilterService
from .orchestrator import AgentOrchestrator, FixtureDispatchGateway
from .refinement import AgentRequestRefiner


class AgentRoutingService:
    def __init__(
        self,
        event_filter: EventFilterService | None = None,
        refiner: AgentRequestRefiner | None = None,
        orchestrator: AgentOrchestrator | None = None,
    ) -> None:
        self.event_filter = event_filter or EventFilterService()
        self.refiner = refiner or AgentRequestRefiner()
        self.orchestrator = orchestrator or AgentOrchestrator(FixtureDispatchGateway())

    def evaluate(self, request: RoutingEvaluationRequest) -> RoutingOutcome:
        decision, metrics, play_context, ignored, accepted = self.event_filter.evaluate(request)
        last = accepted[-1] if accepted else None
        signal = request.control_signal
        period = signal.period if signal else last.period if last else 1
        clock_ms = signal.clock_ms if signal else last.clock_ms if last else 0
        agent_request = self.refiner.refine(
            decision,
            metrics,
            play_context,
            request.preferences,
            period=period,
            clock_ms=clock_ms,
            control_signal=signal,
        )
        dispatch = self.orchestrator.dispatch(agent_request) if agent_request else None
        return RoutingOutcome(
            decision=decision,
            metric_updates=metrics,
            play_context=play_context if accepted else PlayContext(score=0),
            agent_request=agent_request,
            dispatch=dispatch,
            ignored_event_ids=ignored,
        )
