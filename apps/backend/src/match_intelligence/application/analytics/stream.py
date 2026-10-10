"""Procesamiento continuo del flujo de eventos.

Orden en el entorno integrado de Azure::

    Event Hubs match-events (grupo backend)
        → validación y deduplicación (Persona 1)
        → EventOrderTracker (Persona 1, marca tardíos)
        → AnalyticsStreamProcessor (Persona 2)
        → Event Hubs match-insights  y  Blob Storage analytics

El procesador no conoce Azure: depende de puertos. Los momentos se publican
con el perfil neutro; cada espectador recibe su versión personalizada por la
API mediante ``MatchAnalytics``.
"""

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from match_intelligence.application.transport import (
    Clock,
    MessageIdFactory,
    new_message_id,
    utc_now,
)
from match_intelligence.domain.analytics.models import (
    ATTENTION_VERSION,
    ENGINE_VERSION,
    InsightCandidate,
    RelevancePreferences,
)
from match_intelligence.domain.contracts import MatchEvent, MatchMetadata

from .engine import IngestOutcome, MatchStateEngine, StateRevision
from .value_models import ValueModelRegistry


class AnalyticsMessageType(StrEnum):
    SNAPSHOT_UPDATED = "match_snapshot.updated"
    CANDIDATE_PROPOSED = "insight_candidate.proposed"
    CANDIDATE_WITHDRAWN = "insight_candidate.withdrawn"
    STATE_REVISED = "match_state.revised"


class AnalyticsEnvelope(BaseModel):
    """Sobre observable de las salidas de Persona 2."""

    model_config = ConfigDict(extra="forbid")

    message_version: Literal["1"] = "1"
    message_id: str = Field(min_length=1)
    message_type: AnalyticsMessageType
    produced_at: AwareDatetime
    producer: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    source_event_id: str | None = None
    payload: dict[str, Any]


class InsightPublisher(Protocol):
    async def publish(self, envelope: AnalyticsEnvelope) -> None: ...


class MatchMetadataProvider(Protocol):
    async def get(self, match_id: str) -> MatchMetadata | None: ...


class AnalyticsArtifactWriter(Protocol):
    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        """Guarda un archivo del análisis y devuelve su ubicación."""


class StaticMetadataProvider:
    """Metadatos conocidos de antemano, para pruebas y ejecuciones locales."""

    def __init__(self, *metadata: MatchMetadata) -> None:
        self._metadata = {item.match_id: item for item in metadata}

    def add(self, metadata: MatchMetadata) -> None:
        self._metadata[metadata.match_id] = metadata

    async def get(self, match_id: str) -> MatchMetadata | None:
        return self._metadata.get(match_id)


@dataclass(frozen=True, slots=True)
class StreamStepResult:
    match_id: str
    event_id: str
    outcome: str
    published: tuple[AnalyticsMessageType, ...]
    processing_ms: float


@dataclass(slots=True)
class _MatchRun:
    engine: MatchStateEngine
    published: dict[str, InsightCandidate] = field(default_factory=dict)
    proposals: list[dict[str, Any]] = field(default_factory=list)
    withdrawals: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    processing_ms: list[float] = field(default_factory=list)


class AnalyticsStreamProcessor:
    def __init__(
        self,
        metadata_provider: MatchMetadataProvider,
        publisher: InsightPublisher,
        *,
        producer: str = "match-analytics",
        value_models: ValueModelRegistry | None = None,
        preferences: RelevancePreferences | None = None,
        clock: Clock = utc_now,
        message_id_factory: MessageIdFactory = new_message_id,
        timer: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._metadata = metadata_provider
        self._publisher = publisher
        self._producer = producer
        self._value_models = value_models or ValueModelRegistry()
        self._preferences = preferences or RelevancePreferences()
        self._clock = clock
        self._message_id_factory = message_id_factory
        self._timer = timer
        self._runs: dict[str, _MatchRun] = {}
        self._missing_metadata: list[str] = []

    @property
    def missing_metadata_event_ids(self) -> tuple[str, ...]:
        return tuple(self._missing_metadata)

    def engine(self, match_id: str) -> MatchStateEngine | None:
        run = self._runs.get(match_id)
        return run.engine if run else None

    def published_candidates(self, match_id: str) -> list[InsightCandidate]:
        run = self._runs.get(match_id)
        return list(run.published.values()) if run else []

    async def process(self, event: MatchEvent, *, arrival_status: object | None = None) -> StreamStepResult:
        started = self._timer()
        run = await self._run(event.match_id)
        if run is None:
            self._missing_metadata.append(event.event_id)
            return StreamStepResult(event.match_id, event.event_id, "missing_metadata", (), 0.0)

        result = run.engine.ingest(event, arrival_status=arrival_status)
        if result.outcome not in {IngestOutcome.APPLIED, IngestOutcome.REBUILT}:
            return StreamStepResult(
                event.match_id, event.event_id, result.outcome.value, (), self._elapsed(started)
            )

        published: list[AnalyticsMessageType] = []
        snapshot = run.engine.snapshot(video_time_ms=event.video_time_ms)
        await self._send(AnalyticsMessageType.SNAPSHOT_UPDATED, event, snapshot.model_dump(mode="json"))
        published.append(AnalyticsMessageType.SNAPSHOT_UPDATED)
        run.timeline.append({
            "event_id": event.event_id,
            "outcome": result.outcome.value,
            "period": snapshot.period,
            "clock_ms": snapshot.clock_ms,
            "score": snapshot.score,
            "possession_team_id": snapshot.possession_team_id,
            "state_revision": snapshot.state_revision,
        })

        if result.revision is not None:
            await self._send(AnalyticsMessageType.STATE_REVISED, event, _revision_payload(result.revision))
            published.append(AnalyticsMessageType.STATE_REVISED)

        current = {c.candidate_id: c for c in run.engine.attention(self._preferences).candidates}
        for candidate_id, candidate in current.items():
            if run.published.get(candidate_id) == candidate:
                continue
            payload = candidate.model_dump(mode="json")
            await self._send(AnalyticsMessageType.CANDIDATE_PROPOSED, event, payload)
            published.append(AnalyticsMessageType.CANDIDATE_PROPOSED)
            run.proposals.append(payload)
            run.published[candidate_id] = candidate
        for candidate_id in [cid for cid in run.published if cid not in current]:
            payload = {
                "candidate_id": candidate_id,
                "match_id": event.match_id,
                "reason": "state_revision",
                "state_revision": run.engine.revision,
            }
            await self._send(AnalyticsMessageType.CANDIDATE_WITHDRAWN, event, payload)
            published.append(AnalyticsMessageType.CANDIDATE_WITHDRAWN)
            run.withdrawals.append(payload)
            del run.published[candidate_id]

        elapsed = self._elapsed(started)
        run.processing_ms.append(elapsed)
        return StreamStepResult(event.match_id, event.event_id, result.outcome.value, tuple(published), elapsed)

    async def finalize(
        self, match_id: str, writer: AnalyticsArtifactWriter, *, run_id: str
    ) -> list[str]:
        """Guarda el registro del análisis para revisión posterior (RNF-03)."""
        run = self._runs.get(match_id)
        if run is None:
            return []
        report = run.engine.attention(self._preferences)
        files: dict[str, bytes] = {
            "final-snapshot.json": _json(run.engine.snapshot().model_dump(mode="json")),
            "state-timeline.jsonl": _jsonl(run.timeline),
            "candidates.jsonl": _jsonl(run.proposals),
            "withdrawals.jsonl": _jsonl(run.withdrawals),
            "attention-decisions.jsonl": _jsonl(d.model_dump(mode="json") for d in report.decisions),
            "revisions.jsonl": _jsonl(_revision_payload(r) for r in run.engine.revisions),
        }
        manifest = {
            "match_id": match_id,
            "run_id": run_id,
            "engine_version": ENGINE_VERSION,
            "attention_version": ATTENTION_VERSION,
            "late_event_policy": run.engine.policy,
            "profile": self._preferences.profile,
            "events": len(run.engine.events),
            "candidates": len(report.candidates),
            "value_models": [
                {"name": s.name.value, "enabled": s.enabled, "reasons": list(s.reasons)}
                for s in self._value_models.statuses()
            ],
            "processing_ms": _latency_summary(run.processing_ms),
            "files": {name: sha256(content).hexdigest() for name, content in files.items()},
        }
        files["run.json"] = _json(manifest)

        locations = []
        for name, content in files.items():
            content_type = "application/x-ndjson" if name.endswith(".jsonl") else "application/json"
            locations.append(
                await writer.write(
                    match_id=match_id, run_id=run_id, name=name,
                    content=content, content_type=content_type,
                )
            )
        return locations

    async def _run(self, match_id: str) -> _MatchRun | None:
        run = self._runs.get(match_id)
        if run is not None:
            return run
        metadata = await self._metadata.get(match_id)
        if metadata is None:
            return None
        run = _MatchRun(MatchStateEngine(metadata, value_models=self._value_models))
        self._runs[match_id] = run
        return run

    async def _send(
        self, message_type: AnalyticsMessageType, event: MatchEvent, payload: dict[str, Any]
    ) -> None:
        await self._publisher.publish(
            AnalyticsEnvelope(
                message_id=self._message_id_factory(),
                message_type=message_type,
                produced_at=self._clock(),
                producer=self._producer,
                correlation_id=event.match_id,
                source_event_id=event.event_id,
                payload=payload,
            )
        )

    def _elapsed(self, started: float) -> float:
        return (self._timer() - started) * 1_000


def _revision_payload(revision: StateRevision) -> dict[str, Any]:
    payload = asdict(revision)
    payload["reason"] = revision.reason.value
    payload["withdrawn_moment_ids"] = list(revision.withdrawn_moment_ids)
    payload["added_moment_ids"] = list(revision.added_moment_ids)
    return payload


def _json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def _jsonl(rows: object) -> bytes:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]  # type: ignore[union-attr]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def _latency_summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    return {
        "count": len(ordered),
        "mean": round(sum(ordered) / len(ordered), 3),
        "p95": round(p95, 3),
        "max": round(ordered[-1], 3),
    }
