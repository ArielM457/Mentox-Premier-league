from match_intelligence.domain.contracts import (
    AttackDirection,
    EventOutcome,
    EventSource,
    EventType,
    MatchEvent,
    MatchMetadata,
    PeriodDirection,
    Player,
    Position,
    Team,
)
from pydantic import BaseModel, ConfigDict


class ValidationIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: list[str | int]
    code: str
    message: str


class RejectedEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    event_id: str | None
    issues: list[ValidationIssueResponse]


class EventValidationReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted_count: int
    rejected_count: int
    accepted: list[MatchEvent]
    rejected: list[RejectedEventResponse]

__all__ = [
    "AttackDirection",
    "EventOutcome",
    "EventSource",
    "EventType",
    "EventValidationReportResponse",
    "MatchEvent",
    "MatchMetadata",
    "PeriodDirection",
    "Player",
    "Position",
    "RejectedEventResponse",
    "Team",
    "ValidationIssueResponse",
]
