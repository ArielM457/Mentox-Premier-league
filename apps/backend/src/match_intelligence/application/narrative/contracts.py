"""Public contracts for narrative consumers and analytics producers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceFact(StrictModel):
    key: str = Field(min_length=1)
    value: int | float | str
    unit: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    window_ms: int | None = Field(default=None, ge=0)
    formula_version: str | None = None
    source_event_ids: list[str] = Field(min_length=1)


class MatchSnapshot(StrictModel):
    contract_version: Literal["1"] = "1"
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    score: dict[str, int]
    metrics: list[EvidenceFact] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)

    @field_validator("score")
    @classmethod
    def valid_score(cls, score: dict[str, int]) -> dict[str, int]:
        if not score or any(value < 0 for value in score.values()):
            raise ValueError("score must contain nonnegative team totals")
        return score


class InsightCandidate(StrictModel):
    contract_version: Literal["1"] = "1"
    candidate_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    kind: str = Field(min_length=1)
    priority: int = Field(ge=0, le=100)
    selection_reason: str | None = None
    facts: list[EvidenceFact] = Field(min_length=1)
    source_event_ids: list[str] = Field(min_length=1)
    evidence_limits: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def facts_have_sources(self) -> InsightCandidate:
        sources = set(self.source_event_ids)
        if any(not set(fact.source_event_ids) <= sources for fact in self.facts):
            raise ValueError("fact source_event_ids must belong to candidate")
        return self


class ViewerPreferences(StrictModel):
    language: Literal["es", "en", "de", "zh", "hi", "fr", "pt"] = "es"
    mode: Literal["casual", "analyst", "professional_analyst", "player"] = "casual"
    level: Literal["simple", "normal", "advanced"] = "normal"
    favorite_team_id: str | None = None
    favorite_player_id: str | None = None

    @model_validator(mode="after")
    def player_mode_has_player(self) -> ViewerPreferences:
        if self.mode == "player" and not self.favorite_player_id:
            raise ValueError("player mode requires favorite_player_id")
        if self.mode == "professional_analyst":
            self.level = "advanced"
        return self


class NarrativeRequest(StrictModel):
    snapshot: MatchSnapshot
    candidate: InsightCandidate
    preferences: ViewerPreferences

    @model_validator(mode="after")
    def same_match(self) -> NarrativeRequest:
        if self.snapshot.match_id != self.candidate.match_id:
            raise ValueError("snapshot and candidate must belong to same match")
        if (self.snapshot.period, self.snapshot.clock_ms) < (
            self.candidate.period, self.candidate.clock_ms
        ):
            raise ValueError("snapshot cannot precede candidate")
        return self


class Claim(StrictModel):
    """An exact reference to a calculated input fact; text is never authority."""

    key: str
    value: int | float | str
    unit: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    window_ms: int | None = None
    formula_version: str | None = None
    source_event_ids: list[str] = Field(min_length=1)


class NarrativeDraft(StrictModel):
    contract_version: Literal["1"] = "1"
    draft_id: str = Field(min_length=1)
    candidate_id: str | None = None
    match_id: str = Field(min_length=1)
    period: int = Field(ge=1, le=4)
    clock_ms: int = Field(ge=0)
    language: Literal["es", "en", "de", "zh", "hi", "fr", "pt"]
    mode: Literal["casual", "analyst", "professional_analyst", "player"]
    level: Literal["simple", "normal", "advanced"]
    content_kind: Literal["live", "answer", "final"]
    headline: str
    explanation: str
    claims: list[Claim] = Field(default_factory=list)
    source_event_ids: list[str] = Field(default_factory=list)
    applied_preferences: dict[str, str] = Field(default_factory=dict)
    verification_status: Literal["approved", "rejected", "unavailable"]
    verification_reason: str | None = None
    editorial_status: Literal["pending", "approved", "rejected"] | None = None
    original_draft_id: str | None = None

    @model_validator(mode="after")
    def evidence_and_review_state(self) -> NarrativeDraft:
        claim_sources = {
            source for claim in self.claims for source in claim.source_event_ids
        }
        if claim_sources != set(self.source_event_ids):
            raise ValueError("draft sources must equal claim sources")
        if self.content_kind == "final" and self.editorial_status is None:
            raise ValueError("final drafts require editorial status")
        return self

    @property
    def publishable(self) -> bool:
        return self.verification_status == "approved" and (
            self.content_kind != "final" or self.editorial_status == "approved"
        )


class DecisionRecord(StrictModel):
    candidate_id: str | None = None
    match_id: str
    action: Literal["selected", "discarded", "rejected", "unavailable", "corrected"]
    reason: str
    source_event_ids: list[str] = Field(default_factory=list)
    elapsed_ms: int = Field(ge=0)
    stage_elapsed_ms: dict[str, int] = Field(default_factory=dict)


class NarrativeOutcome(StrictModel):
    draft: NarrativeDraft | None
    decision: DecisionRecord


class QuestionRequest(StrictModel):
    snapshot: MatchSnapshot
    candidates: list[InsightCandidate] = Field(default_factory=list)
    preferences: ViewerPreferences
    question: str = Field(min_length=1)

    @model_validator(mode="after")
    def same_match(self) -> QuestionRequest:
        if any(item.match_id != self.snapshot.match_id for item in self.candidates):
            raise ValueError("question candidates must belong to snapshot match")
        return self


class SummaryRequest(StrictModel):
    snapshot: MatchSnapshot
    candidates: list[InsightCandidate] = Field(min_length=1)
    preferences: ViewerPreferences
    match_finished: Literal[True]

    @model_validator(mode="after")
    def same_match(self) -> SummaryRequest:
        if any(item.match_id != self.snapshot.match_id for item in self.candidates):
            raise ValueError("summary candidates must belong to snapshot match")
        return self


class ErrorReport(StrictModel):
    report_id: str = Field(min_length=1)
    draft: NarrativeDraft
    reason: str = Field(min_length=1)
    snapshot: MatchSnapshot
    candidate: InsightCandidate | None = None


class ReportResolution(StrictModel):
    report_id: str
    status: Literal["confirmed_error", "insufficient_evidence", "no_error"]
    reason: str
    original_draft_id: str
    correction: NarrativeDraft | None = None
    source_event_ids: list[str] = Field(default_factory=list)
