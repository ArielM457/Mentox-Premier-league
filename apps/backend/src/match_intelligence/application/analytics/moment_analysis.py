"""Análisis de un momento para la pantalla de resumen (Persona 2).

Junta, para un momento ya mostrado, lo que la analítica sabe de él: por qué el
motor de atención lo eligió (prioridad y motivos con puntos), sus hechos con
unidades y eventos de origen, las posiciones del instante y las lecturas
«¿qué habría pasado si…?» medidas con esas posiciones.

Los identificadores de momento son ``moment-<evento ancla>`` en el motor de
Persona 2 y en el provisional de Persona 4, así que el análisis funciona con
los dos.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.domain.analytics.models import (
    ATTENTION_VERSION,
    ENGINE_VERSION,
    MetricValue,
    SelectionReason,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.analytics.state import chronological
from match_intelligence.domain.analytics.tracking import TrackingFrame, TrackSet
from match_intelligence.domain.analytics.what_if import (
    WhatIfReading,
    frame_at,
    what_if_readings,
)
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata

from .pipeline import MatchAnalytics

MOMENT_PREFIX = "moment-"


class MomentNotFound(LookupError):
    """El momento no corresponde a ningún evento del partido."""


class MomentAnalysis(BaseModel):
    """Lo que la analítica sabe de un momento, para explicarlo en pantalla."""

    model_config = ConfigDict(extra="forbid")

    match_id: str
    candidate_id: str
    anchor_event_id: str
    period: int
    clock_ms: int
    video_time_ms: int | None = None
    engine_version: str = ENGINE_VERSION
    attention_version: str = ATTENTION_VERSION
    found_in_engine: bool = Field(
        description="El motor de Persona 2 detecta un momento en ese evento"
    )
    kind: str | None = None
    outcome: str | None = Field(default=None, description="emitted o discarded para el perfil")
    priority: int | None = None
    threshold: int | None = None
    reasons: list[SelectionReason] = Field(default_factory=list)
    facts: list[MetricValue] = Field(default_factory=list)
    source_event_ids: list[str] = Field(default_factory=list)
    evidence_limits: list[str] = Field(default_factory=list)
    frame: TrackingFrame | None = None
    what_if: list[WhatIfReading] = Field(default_factory=list)


def anchor_of(candidate_id: str, anchor_event_id: str | None) -> str:
    if anchor_event_id:
        return anchor_event_id
    if candidate_id.startswith(MOMENT_PREFIX):
        return candidate_id[len(MOMENT_PREFIX):]
    raise MomentNotFound(f"No se puede ubicar el momento {candidate_id}")


def analyze_moment(
    metadata: MatchMetadata,
    events: Sequence[MatchEvent],
    *,
    candidate_id: str,
    anchor_event_id: str | None = None,
    tracks: TrackSet | None = None,
    preferences: object | None = None,
    analytics: MatchAnalytics | None = None,
) -> MomentAnalysis:
    """Analiza el momento con los eventos ocurridos hasta su evento ancla."""
    anchor_id = anchor_of(candidate_id, anchor_event_id)
    ordered = chronological(events)
    position = next((i for i, e in enumerate(ordered) if e.event_id == anchor_id), None)
    if position is None:
        raise MomentNotFound(f"No existe el evento {anchor_id} en el partido {metadata.match_id}")
    anchor = ordered[position]
    seen = ordered[: position + 1]

    analytics = analytics or MatchAnalytics()
    report = analytics.attention_report(metadata, seen, preferences)
    candidate = next((c for c in report.candidates if c.anchor_event_id == anchor_id), None)
    decision = next((d for d in report.decisions if d.anchor_event_id == anchor_id), None)

    source_ids = candidate.source_event_ids if candidate else [anchor_id]
    by_id = {e.event_id: e for e in seen}
    sources = [by_id[i] for i in source_ids if i in by_id] or [anchor]

    frame = None
    readings: list[WhatIfReading] = []
    if tracks is not None:
        frame = frame_at(tracks, anchor.period, anchor.clock_ms, anchor.video_time_ms)
        readings = what_if_readings(tracks, PitchFrame.from_metadata(metadata), anchor, sources)

    return MomentAnalysis(
        match_id=metadata.match_id,
        candidate_id=candidate_id,
        anchor_event_id=anchor_id,
        period=anchor.period,
        clock_ms=anchor.clock_ms,
        video_time_ms=anchor.video_time_ms,
        found_in_engine=decision is not None,
        kind=decision.kind if decision else None,
        outcome=decision.outcome.value if decision else None,
        priority=decision.priority if decision else None,
        threshold=decision.threshold if decision else None,
        reasons=list(decision.reasons) if decision else [],
        facts=list(candidate.facts) if candidate else [],
        source_event_ids=[e.event_id for e in sources],
        evidence_limits=list(candidate.evidence_limits) if candidate else [],
        frame=frame,
        what_if=readings,
    )
