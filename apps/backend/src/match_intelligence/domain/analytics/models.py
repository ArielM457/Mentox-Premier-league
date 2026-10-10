"""Contratos de Persona 2: ``MatchSnapshot v1`` e ``InsightCandidate v1``.

Conservan los campos de ``docs/plan-de-desarrollo/contratos-de-trabajo.md`` y
de los modelos provisionales de Persona 4 con el mismo nombre y tipo. Los
campos añadidos son opcionales y explican de dónde sale cada cifra y por qué
se emitió o descartó cada momento.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

ENGINE_VERSION = "match-state@1"
ATTENTION_VERSION = "attention@1"

Number = int | float


class MetricOrigin(StrEnum):
    """Distingue un conteo de un cálculo, de una escala propia y de un modelo."""

    EVENT_COUNT = "event_count"
    DERIVED = "derived"
    TEAM_INDICATOR = "team_indicator"
    VALUE_MODEL = "value_model"


class IndicatorComponent(BaseModel):
    """Parte visible de un indicador propio o de una métrica compuesta."""

    model_config = ConfigDict(extra="forbid")

    key: str
    team_id: str | None = None
    value: Number | None = None
    unit: str
    weight: float | None = None
    reference: float | None = Field(
        default=None, description="Valor que satura el componente; definido por el equipo"
    )
    contribution: float | None = Field(
        default=None, description="Aporte del componente al valor final"
    )
    source_event_ids: list[str] = Field(default_factory=list)


class MetricValue(BaseModel):
    """Cifra trazable. Si faltan datos queda ``available=False`` y sin valor."""

    model_config = ConfigDict(extra="forbid")

    key: str
    team_id: str | None = None
    player_id: str | None = None
    value: Number | None = Field(
        default=None, description="Ausente cuando no hay datos suficientes; nunca se usa cero"
    )
    available: bool = True
    unit: str
    window_ms: int | None = None
    formula_version: str = "1"
    source_event_ids: list[str] = Field(default_factory=list)
    origin: MetricOrigin = MetricOrigin.EVENT_COUNT
    period: int | None = None
    window_start_clock_ms: int | None = None
    window_end_clock_ms: int | None = None
    unavailable_reason: str | None = None
    components: list[IndicatorComponent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _availability_matches_value(self) -> Self:
        if self.available and self.value is None:
            raise ValueError("Una métrica disponible necesita un valor")
        if not self.available and self.value is not None:
            raise ValueError("Una métrica no disponible no lleva valor")
        return self


class MatchSnapshot(BaseModel):
    """``MatchSnapshot v1``: estado reproducible desde eventos normalizados."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    match_id: str
    period: int
    clock_ms: int
    video_time_ms: int | None = None
    score: dict[str, int]
    possession_team_id: str | None = None
    metrics: list[MetricValue] = Field(default_factory=list)
    recent_event_ids: list[str] = Field(default_factory=list)
    engine_version: str = ENGINE_VERSION
    event_count: int = 0
    last_event_id: str | None = None
    last_event_clock_ms: int | None = None
    state_revision: int = 0
    late_event_ids: list[str] = Field(default_factory=list)
    corrected_event_ids: list[str] = Field(default_factory=list)
    excluded_event_ids: list[str] = Field(default_factory=list)


class SelectionReason(BaseModel):
    """Motivo con los puntos que sumó o restó a la prioridad."""

    model_config = ConfigDict(extra="forbid")

    code: str
    points: int = 0
    detail: str
    params: dict[str, str | int | float | None] = Field(default_factory=dict)


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
    video_time_ms: int | None = None
    anchor_event_id: str | None = None
    sequence_id: str | None = None
    signals: list[str] = Field(default_factory=list)
    reasons: list[SelectionReason] = Field(default_factory=list)
    attention_version: str = ATTENTION_VERSION


class AttentionOutcome(StrEnum):
    EMITTED = "emitted"
    DISCARDED = "discarded"


class AttentionDecision(BaseModel):
    """Registro de por qué un momento se emitió o se descartó."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    match_id: str
    anchor_event_id: str
    period: int
    clock_ms: int
    kind: str
    team_id: str | None = None
    outcome: AttentionOutcome
    priority: int = Field(ge=0, le=100)
    threshold: int = Field(ge=0, le=100)
    profile: str
    reasons: list[SelectionReason] = Field(default_factory=list)
    attention_version: str = ATTENTION_VERSION


class RelevanceMode(StrEnum):
    CASUAL = "casual"
    ANALYST = "analyst"
    PLAYER = "player"


class RelevancePreferences(BaseModel):
    """Preferencias que Persona 2 usa solo para puntuar relevancia.

    Acepta el objeto de preferencias de Persona 4 e ignora el idioma y el
    nivel, que no cambian qué es importante. ``mode=None`` es el perfil neutro
    que usa el flujo publicado en Azure.
    """

    model_config = ConfigDict(extra="ignore")

    mode: RelevanceMode | None = None
    favorite_team_id: str | None = None
    favorite_player_id: str | None = None

    @classmethod
    def from_any(cls, preferences: object | None) -> "RelevancePreferences":
        if preferences is None:
            return cls()
        if isinstance(preferences, RelevancePreferences):
            return preferences
        if isinstance(preferences, BaseModel):
            return cls.model_validate(preferences.model_dump(mode="json"))
        if isinstance(preferences, Mapping):
            return cls.model_validate(dict(preferences))
        return cls.model_validate(preferences, from_attributes=True)

    @property
    def profile(self) -> str:
        parts = [f"mode={self.mode.value if self.mode else 'neutral'}"]
        if self.favorite_team_id:
            parts.append(f"team={self.favorite_team_id}")
        if self.favorite_player_id:
            parts.append(f"player={self.favorite_player_id}")
        return ";".join(parts)
