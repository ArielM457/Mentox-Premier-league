"""HTTP access to the narrative module for local integration and clients."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from match_intelligence.application.narrative.contracts import (
    ErrorReport,
    NarrativeOutcome,
    NarrativeRequest,
    QuestionRequest,
    ReportResolution,
    SummaryRequest,
)
from match_intelligence.application.narrative.gateway import FixtureGateway
from match_intelligence.application.narrative.service import NarrativeService

router = APIRouter(prefix="/api/v1/narratives", tags=["Narrativa"])


def narrative_service(provider: Literal["fixture", "azure"] = "azure") -> NarrativeService:
    if provider == "fixture":
        return NarrativeService(FixtureGateway())
    try:
        from match_intelligence.adapters.agents.crewai_gateway import CrewAIGateway

        return NarrativeService(CrewAIGateway())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/live", response_model=NarrativeOutcome)
def create_live(
    request: NarrativeRequest,
    service: NarrativeService = Depends(narrative_service),
) -> NarrativeOutcome:
    """Generate one verified live draft from state and a candidate."""
    return service.create_live(request)


@router.post("/questions", response_model=NarrativeOutcome)
def answer_question(
    request: QuestionRequest,
    service: NarrativeService = Depends(narrative_service),
) -> NarrativeOutcome:
    """Answer from available metrics and candidate facts."""
    return service.answer(request)


@router.post("/summaries", response_model=NarrativeOutcome)
def create_summary(
    request: SummaryRequest,
    service: NarrativeService = Depends(narrative_service),
) -> NarrativeOutcome:
    """Create a final draft that still requires editorial approval."""
    return service.summarize(request)


@router.post("/reports/resolve", response_model=ReportResolution)
def resolve_report(report: ErrorReport) -> ReportResolution:
    """Check a report against original evidence and propose a correction."""
    return NarrativeService(FixtureGateway()).resolve_report(report)
