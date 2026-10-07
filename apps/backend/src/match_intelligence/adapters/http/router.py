from fastapi import APIRouter

from .schemas import MatchEvent, MatchMetadata

router = APIRouter(prefix="/api/v1", tags=["Sistema y contratos"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/events/validate")
def validate_event(event: MatchEvent) -> dict[str, object]:
    """Valida el contrato; todavía no ingiere ni guarda el evento."""
    return {"valid": True, "event": event.model_dump(mode="json")}


@router.post("/matches/validate")
def validate_match(match: MatchMetadata) -> dict[str, object]:
    """Valida los metadatos; todavía no crea ni guarda el partido."""
    return {"valid": True, "match": match.model_dump(mode="json")}
