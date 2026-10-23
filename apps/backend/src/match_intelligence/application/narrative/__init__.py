"""Narrative application service and public contracts."""

from .contracts import (
    ErrorReport,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    NarrativeRequest,
    QuestionRequest,
    SummaryRequest,
    ViewerPreferences,
)
from .service import NarrativeService

__all__ = [
    "ErrorReport",
    "InsightCandidate",
    "MatchSnapshot",
    "NarrativeDraft",
    "NarrativeRequest",
    "NarrativeService",
    "QuestionRequest",
    "SummaryRequest",
    "ViewerPreferences",
]
