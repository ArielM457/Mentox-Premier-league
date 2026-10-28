"""Contratos de trabajo v1 entre analítica, narración y pantalla.

Siguen los ejemplos de ``docs/desarrollo/contratos.md``.
``MatchSnapshot`` e ``InsightCandidate`` pertenecen a Persona 2 y
``NarrativeDraft`` a Persona 3; se definen aquí para que la API y el frontend
puedan avanzar con ejemplos mientras esos módulos se implementan.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Language(StrEnum):
    ES = "es"
    EN = "en"
    DE = "de"
    ZH = "zh"
    HI = "hi"
    FR = "fr"
    PT = "pt"


class SummaryType(StrEnum):
    SHORT = "short"
    EXTENDED = "extended"
    PLAYER_DANGER = "player_danger"


class ViewerMode(StrEnum):
    CASUAL = "casual"
    ANALYST = "analyst"
    PROFESSIONAL_ANALYST = "professional_analyst"
    PLAYER = "player"


class DetailLevel(StrEnum):
    SIMPLE = "simple"
    NORMAL = "normal"
    ADVANCED = "advanced"


class ViewerPreferences(BaseModel):
    """Preferencias del espectador que entrega Persona 4."""

    model_config = ConfigDict(extra="forbid")

    language: Language = Language.ES
    mode: ViewerMode = ViewerMode.CASUAL
    level: DetailLevel = DetailLevel.NORMAL
    favorite_team_id: str | None = None
    favorite_player_id: str | None = None

    @model_validator(mode="after")
    def professional_mode_uses_advanced_detail(self) -> "ViewerPreferences":
        if self.mode is ViewerMode.PROFESSIONAL_ANALYST:
            self.level = DetailLevel.ADVANCED
        return self


class MetricValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    team_id: str | None = None
    player_id: str | None = None
    value: float | None = Field(
        default=None, description="Ausente cuando no hay datos suficientes; nunca se usa cero"
    )
    available: bool = True
    unit: str
    window_ms: int | None = None
    formula_version: str = "1"
    source_event_ids: list[str] = Field(default_factory=list)


class MatchSnapshot(BaseModel):
    """``MatchSnapshot v1``: estado reproducible del partido."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    match_id: str
    period: int
    clock_ms: int
    video_time_ms: int
    score: dict[str, int]
    possession_team_id: str | None = None
    metrics: list[MetricValue] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)


class InsightCandidate(BaseModel):
    """``InsightCandidate v1``: momento propuesto con hechos y evidencia."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    candidate_id: str
    match_id: str
    period: int
    clock_ms: int
    kind: str
    priority: int = Field(ge=0, le=100)
    team_id: str | None = None
    player_ids: list[str] = Field(default_factory=list)
    facts: list[MetricValue] = Field(default_factory=list)
    source_event_ids: list[str] = Field(min_length=1)
    evidence_limits: list[str] = Field(default_factory=list)


class VerificationStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class EditorialStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ContentKind(StrEnum):
    LIVE = "live"
    FINAL = "final"
    ANSWER = "answer"


class NarrativeDraft(BaseModel):
    """``NarrativeDraft v1``: texto propuesto por Persona 3."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    draft_id: str
    candidate_id: str | None
    match_id: str
    language: Language
    mode: ViewerMode
    level: DetailLevel = DetailLevel.NORMAL
    content_kind: ContentKind
    headline: str
    explanation: str
    applied_preferences: list[str] = Field(default_factory=list)
    source_event_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus
    editorial_status: EditorialStatus | None = None


class OverlayMessage(BaseModel):
    """``OverlayMessage v1``: mensaje legible por máquina para la pantalla (RF-19)."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    message_id: str
    draft_id: str
    candidate_id: str | None
    match_id: str
    period: int
    clock_ms: int
    video_time_ms: int
    video_time_basis: Literal["source_event_timestamp"] = "source_event_timestamp"
    show_for_ms: int = Field(gt=0)
    priority: int = Field(ge=0, le=100)
    kind: str
    language: Language
    mode: ViewerMode
    level: DetailLevel
    headline: str
    explanation: str
    call_to_action: str = Field(default="Descubre por qué importa", min_length=1)
    source_event_ids: list[str]
    display_until_ms: int = Field(
        description="Fin efectivo en el vídeo; menor que video_time_ms + show_for_ms si otro mensaje lo reemplaza"
    )
    replaces_message_id: str | None = Field(
        default=None, description="Mensaje que este reemplaza en la misma zona de pantalla (RNF-05)"
    )
    suppressed: bool = Field(
        default=False,
        description="No ocupa la zona principal porque había otro de mayor prioridad; queda en el historial",
    )
    corrected: bool = Field(default=False, description="Versión corregida tras un reporte (RF-39)")
