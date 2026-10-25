"""HTTP access to deterministic event filtering and agent dispatch."""

from fastapi import APIRouter, HTTPException

from match_intelligence.adapters.messaging.routing_transport import build_routing_transport

from match_intelligence.application.routing import (
    RoutingEvaluationRequest,
    RoutingOutcome,
    RoutedEventPipeline,
)


router = APIRouter(prefix="/api/v1/agent-routing", tags=["Enrutamiento de agentes"])
routing_pipeline = RoutedEventPipeline(build_routing_transport())


@router.post("/evaluate", response_model=RoutingOutcome)
async def evaluate_routing(request: RoutingEvaluationRequest) -> RoutingOutcome:
    """Filter one event window and dispatch only relevant agent work."""
    try:
        return await routing_pipeline.evaluate(request)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo entregar el evento conservando su garantía: {type(error).__name__}",
        ) from error


@router.get("/status")
async def routing_status() -> dict[str, object]:
    """Expone contadores operativos sin revelar credenciales ni mensajes."""
    return routing_pipeline.status()
