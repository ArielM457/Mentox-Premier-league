from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.domain.contracts import MatchEvent, MatchMetadata
from match_intelligence.domain.presentation import (
    EditorialStatus,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    OverlayMessage,
    ViewerPreferences,
)

ErrorKind = Literal["goal", "shot", "recovery", "turnover", "progressive_pass", "pressure"]


class ErrorResponse(BaseModel):
    detail: str


class LoadMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Literal["acceptance", "analytics"] = Field(
        default="acceptance",
        description="acceptance: partido corto de Persona 1. analytics: partido de dos tiempos de Persona 2",
    )
    seed: int | None = Field(default=None, description="Semilla del generador; por defecto la del escenario")
    match_id: str = Field(default="synthetic-acceptance-001", min_length=1)
    inject_error_in: ErrorKind | None = Field(
        default=None,
        description="Provoca un error controlado en la narración de ese tipo de momento para demostrar reportes (RF-39)",
    )


class VideoSource(BaseModel):
    kind: Literal["synthetic_timeline", "file"] = "synthetic_timeline"
    url: str | None = None
    timing_basis: Literal["source_event_timestamp"] = "source_event_timestamp"


class MatchListItem(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    duration_ms: int
    event_count: int
    created_at: datetime


class MatchDetailResponse(BaseModel):
    metadata: MatchMetadata
    duration_ms: int
    event_count: int
    video: VideoSource


class EventsResponse(BaseModel):
    until_video_ms: int
    events: list[MatchEvent]


class OverlaysResponse(BaseModel):
    until_video_ms: int
    preferences: ViewerPreferences
    pipeline_ms: float = Field(description="Tiempo de cálculo desde eventos hasta mensajes")
    overlays: list[OverlayMessage]


class SourcesResponse(BaseModel):
    draft: NarrativeDraft
    events: list[MatchEvent]


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)
    video_time_ms: int = Field(ge=0)
    preferences: ViewerPreferences = Field(default_factory=ViewerPreferences)


class AnswerResponse(BaseModel):
    answer: NarrativeDraft
    snapshot: MatchSnapshot


class EditorialRecordResponse(BaseModel):
    draft: NarrativeDraft
    status: EditorialStatus
    reviewer: str | None
    note: str | None
    decided_at: datetime | None


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: str = Field(min_length=1)
    message_id: str | None = None
    reason: str = Field(min_length=1, max_length=500)


class ReportResponse(BaseModel):
    report_id: str
    draft_id: str
    message_id: str | None
    reason: str
    outcome: Literal["confirmed", "withdrawn"]
    issues: list[str]
    corrected_draft: NarrativeDraft | None
    created_at: datetime


class PlaybackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["play", "pause", "seek", "restart"]
    video_time_ms: int | None = Field(default=None, ge=0)


class PlaybackResponse(BaseModel):
    match_id: str
    state: Literal["playing", "paused"]
    video_time_ms: int
    events_applied: int
    duration_ms: int


class AnalystMomentResponse(BaseModel):
    candidate: InsightCandidate
    video_time_ms: int
    drafts: dict[Literal["casual", "analyst"], NarrativeDraft] = Field(
        description="Lo que se generó para cada modo con los mismos hechos (RF-23)"
    )
    shown_in: list[Literal["casual", "analyst"]] = Field(description="Modos en que el momento llegó a la pantalla")


class AnalystFeedResponse(BaseModel):
    until_video_ms: int
    pipeline_ms: float
    snapshot: MatchSnapshot
    events: list[MatchEvent]
    moments: list[AnalystMomentResponse]
    commentary: list[OverlayMessage] = Field(
        description="Comentario en vivo completo, incluidos los mensajes en cola o reemplazados"
    )
