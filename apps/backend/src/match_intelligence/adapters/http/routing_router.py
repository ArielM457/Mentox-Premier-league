"""HTTP access to deterministic event filtering and agent dispatch."""

from fastapi import APIRouter

from match_intelligence.application.routing import (
    AgentRoutingService,
    RoutingEvaluationRequest,
    RoutingOutcome,
)


router = APIRouter(prefix="/api/v1/agent-routing", tags=["Enrutamiento de agentes"])


@router.post("/evaluate", response_model=RoutingOutcome)
def evaluate_routing(request: RoutingEvaluationRequest) -> RoutingOutcome:
    """Filter one event window and dispatch only relevant agent work."""
    return AgentRoutingService().evaluate(request)
