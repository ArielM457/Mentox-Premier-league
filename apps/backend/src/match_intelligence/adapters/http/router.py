from fastapi import APIRouter

from match_intelligence.application.validation import validate_event_batch

from .schemas import EventValidationReportResponse, MatchEvent, MatchMetadata

router = APIRouter(prefix="/api/v1", tags=["Sistema y contratos"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/events/validate")
def validate_event(event: MatchEvent) -> dict[str, object]:
    """Valida el contrato; todavía no ingiere ni guarda el evento."""
    return {"valid": True, "event": event.model_dump(mode="json")}


@router.post(
    "/events/validate-batch",
    response_model=EventValidationReportResponse,
)
def validate_events(events: list[object]) -> dict[str, object]:
    """Valida todo el lote y conserva los rechazos para diagnóstico."""
    report = validate_event_batch(events)
    return {
        "accepted_count": report.accepted_count,
        "rejected_count": report.rejected_count,
        "accepted": [event.model_dump(mode="json") for event in report.accepted],
        "rejected": [
            {
                "index": rejected.index,
                "event_id": rejected.event_id,
                "issues": [
                    {
                        "location": list(issue.location),
                        "code": issue.code,
                        "message": issue.message,
                    }
                    for issue in rejected.issues
                ],
            }
            for rejected in report.rejected
        ],
    }


@router.post("/matches/validate")
def validate_match(match: MatchMetadata) -> dict[str, object]:
    """Valida los metadatos; todavía no crea ni guarda el partido."""
    return {"valid": True, "match": match.model_dump(mode="json")}
