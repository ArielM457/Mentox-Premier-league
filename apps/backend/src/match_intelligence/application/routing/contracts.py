"""Versioned contracts for filtering and dispatching match intelligence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from match_intelligence.application.narrative.contracts import ViewerPreferences


Route = Literal[
    "metrics_only",
    "moment_candidate",
    "danger_immediate",
    "dead_ball_context",
    "recap",
    "rejected",
]
AgentTask = Literal[
    "danger_simulation",
    "moment_selector",
    "narrator",
    "recap",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Position(StrictModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class RoutingEvent(StrictModel):
    """Application copy of MatchEvent 1.0, independent of HTTP adapters."""

    schema_version: Literal["1.0"]
    event_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int | None = Field(default=None, ge=0)
    type: Literal["pass", "shot", "tackle", "possession_change", "pressure", "recovery"]
    team_id: str = Field(min_length=1)
    player_id: str | None = None
    start: Position | None = None
    end: Position | None = None
    outcome: Literal["success", "failure", "goal", "saved", "blocked", "off_target", "unknown"] = "unknown"
    source: Literal["synthetic", "video_model"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    related_event_ids: list[str] = Field(default_factory=list)


class ControlSignal(StrictModel):
    type: Literal["play_stopped", "period_ended", "match_ended"]
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    video_time_ms: int | None = Field(default=None, ge=0)
    reason: str | None = None


class MetricUpdate(StrictModel):
    key: str
    team_id: str
    value: int | float
    unit: str = "count"
    formula_version: Literal["1"] = "1"
    source_event_ids: list[str] = Field(min_length=1)


class RoutingDecision(StrictModel):
    contract_version: Literal["1"] = "1"
    decision_id: str
    match_id: str
    route: Route
    priority: int = Field(ge=0, le=100)
    reason_codes: list[str] = Field(min_length=1)
    source_event_ids: list[str] = Field(default_factory=list)
    rule_version: Literal["1"] = "1"


class PlayContext(StrictModel):
    contract_version: Literal["1"] = "1"
    pattern_key: str | None = None
    match_status: Literal["confirmed", "partial", "none"] = "none"
    score: float = Field(ge=0, le=1)
    signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    source_event_ids: list[str] = Field(default_factory=list)


class AgentRequest(StrictModel):
    contract_version: Literal["1"] = "1"
    request_id: str
    match_id: str
    task: AgentTask
    priority: int = Field(ge=0, le=100)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    ttl_ms: int = Field(gt=0)
    source_event_ids: list[str] = Field(default_factory=list)
    metrics: list[MetricUpdate] = Field(default_factory=list)
    play_context: PlayContext
    preferences: ViewerPreferences
    control_signal: ControlSignal | None = None


class AgentDispatch(StrictModel):
    contract_version: Literal["1"] = "1"
    dispatch_id: str
    request_id: str
    match_id: str
    target_agent: AgentTask
    priority: int = Field(ge=0, le=100)
    ttl_ms: int = Field(gt=0)
    correlation_id: str
    idempotency_key: str
    reason: str


class RoutingEvaluationRequest(StrictModel):
    match_id: str = Field(min_length=1)
    events: list[RoutingEvent] = Field(default_factory=list)
    control_signal: ControlSignal | None = None
    existing_event_ids: list[str] = Field(default_factory=list)
    preferences: ViewerPreferences = Field(default_factory=ViewerPreferences)

    @model_validator(mode="after")
    def valid_window(self) -> RoutingEvaluationRequest:
        if not self.events and self.control_signal is None:
            raise ValueError("events or control_signal is required")
        if any(event.match_id != self.match_id for event in self.events):
            raise ValueError("all events must belong to match_id")
        return self


class RoutingOutcome(StrictModel):
    decision: RoutingDecision
    metric_updates: list[MetricUpdate] = Field(default_factory=list)
    play_context: PlayContext
    agent_request: AgentRequest | None = None
    dispatch: AgentDispatch | None = None
    ignored_event_ids: list[str] = Field(default_factory=list)
