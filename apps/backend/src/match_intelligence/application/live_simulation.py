"""Simulación local del ingreso, las colas, los agentes y los recortes destacados."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.match_session import MatchSession
from match_intelligence.application.routing import AgentRoutingService
from match_intelligence.application.routing.contracts import (
    ControlSignal,
    Position,
    RoutingEvaluationRequest,
    RoutingEvent,
)
from match_intelligence.application.narrative.contracts import ViewerPreferences as RoutingPreferences
from match_intelligence.domain.presentation import ViewerPreferences


class SimulationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    label: str
    route: str
    queue: Literal["metrics", "important", "discarded"]
    target_agent: str | None = None
    agent_called: bool
    reason_codes: list[str]
    source_event_ids: list[str]


class HighlightClip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clip_id: str
    match_id: str
    message_id: str
    draft_id: str
    start_video_ms: int = Field(ge=0)
    end_video_ms: int = Field(gt=0)
    headline: str
    source_event_ids: list[str]
    status: Literal["pending", "approved", "rejected"] = "pending"
    reviewer: str | None = None
    blob_name: str | None = None


class SimulationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_id: str
    match_id: str
    started_at: datetime
    ingress_events: int
    metrics_queue: int
    important_queue: int
    discarded: int
    generated_messages: int
    summary_draft_id: str | None
    steps: list[SimulationStep]
    highlights: list[HighlightClip]


class LocalSimulationStore:
    def __init__(self) -> None:
        self.reports: dict[str, SimulationReport] = {}
        self.highlights: dict[str, dict[str, HighlightClip]] = {}

    def save(self, report: SimulationReport) -> None:
        self.reports[report.match_id] = report
        self.highlights[report.match_id] = {item.clip_id: item for item in report.highlights}

    def clips(self, match_id: str) -> list[HighlightClip]:
        return list(self.highlights.get(match_id, {}).values())

    def review(self, match_id: str, clip_id: str, decision: str, reviewer: str) -> HighlightClip:
        clip = self.highlights.get(match_id, {}).get(clip_id)
        if clip is None:
            raise KeyError(clip_id)
        updated = clip.model_copy(update={"status": decision, "reviewer": reviewer})
        self.highlights[match_id][clip_id] = updated
        return updated


simulation_store = LocalSimulationStore()


def _event(match_id: str, event_id: str, clock: int, kind: str, team: str, **changes) -> RoutingEvent:
    values = {
        "schema_version": "1.0",
        "event_id": event_id,
        "match_id": match_id,
        "period": 1,
        "clock_ms": clock,
        "video_time_ms": clock,
        "type": kind,
        "team_id": team,
        "player_id": None,
        "outcome": "success",
        "source": "synthetic",
    }
    values.update(changes)
    return RoutingEvent.model_validate(values)


def _scenarios(match_id: str, team_id: str, preferences: RoutingPreferences):
    normal = _event(match_id, "sim-pass", 1_000, "pass", team_id, start=Position(x=15, y=40), end=Position(x=25, y=42))
    recovery = _event(match_id, "sim-recovery", 2_000, "recovery", team_id, start=Position(x=38, y=50))
    pass_one = _event(match_id, "sim-pass-1", 3_000, "pass", team_id, start=Position(x=38, y=50), end=Position(x=58, y=48))
    pass_two = _event(match_id, "sim-pass-2", 4_000, "pass", team_id, start=Position(x=58, y=48), end=Position(x=80, y=50))
    shot = _event(match_id, "sim-shot", 5_000, "shot", team_id, start=Position(x=86, y=50), end=Position(x=100, y=50), outcome="blocked")
    return [
        ("metrics-only", "Pase normal", RoutingEvaluationRequest(match_id=match_id, events=[normal], preferences=preferences)),
        ("narrative-candidate", "Recuperación y progresión", RoutingEvaluationRequest(match_id=match_id, events=[recovery, pass_one, pass_two], preferences=preferences)),
        ("immediate-danger", "Tiro en zona peligrosa", RoutingEvaluationRequest(match_id=match_id, events=[shot], preferences=preferences)),
        ("dead-ball", "Juego detenido", RoutingEvaluationRequest(match_id=match_id, control_signal=ControlSignal(type="play_stopped", period=1, clock_ms=6_000), preferences=preferences)),
        ("recap", "Fin del partido", RoutingEvaluationRequest(match_id=match_id, control_signal=ControlSignal(type="match_ended", period=2, clock_ms=2_700_000), preferences=preferences)),
        ("duplicate", "Evento duplicado", RoutingEvaluationRequest(match_id=match_id, events=[normal], existing_event_ids=[normal.event_id], preferences=preferences)),
    ]


def run_local_simulation(session: MatchSession, preferences: ViewerPreferences) -> SimulationReport:
    routing_preferences = RoutingPreferences.model_validate(preferences.model_dump(mode="json"))
    service = AgentRoutingService()
    steps: list[SimulationStep] = []
    for scenario_id, label, request in _scenarios(session.match_id, session.metadata.home_team.team_id, routing_preferences):
        outcome = service.evaluate(request)
        route = outcome.decision.route
        queue = "metrics" if route == "metrics_only" else "discarded" if route == "rejected" else "important"
        steps.append(SimulationStep(
            scenario_id=scenario_id,
            label=label,
            route=route,
            queue=queue,
            target_agent=outcome.dispatch.target_agent if outcome.dispatch else None,
            agent_called=outcome.dispatch is not None,
            reason_codes=outcome.decision.reason_codes,
            source_event_ids=outcome.decision.source_event_ids,
        ))

    batch = session.overlays(preferences, until_video_ms=session.duration_ms)
    summary = session.summary(preferences)
    clips = [
        HighlightClip(
            clip_id=f"clip-{item.message_id}",
            match_id=session.match_id,
            message_id=item.message_id,
            draft_id=item.draft_id,
            start_video_ms=max(0, item.video_time_ms - 5_000),
            end_video_ms=min(session.duration_ms, item.video_time_ms + 8_000),
            headline=item.headline,
            source_event_ids=item.source_event_ids,
        )
        for item in batch.overlays
        if not item.suppressed and item.priority >= 70
    ]
    now = datetime.now(UTC)
    report = SimulationReport(
        simulation_id=f"simulation-{session.match_id}-{int(now.timestamp())}",
        match_id=session.match_id,
        started_at=now,
        ingress_events=6,
        metrics_queue=sum(item.queue == "metrics" for item in steps),
        important_queue=sum(item.queue == "important" for item in steps),
        discarded=sum(item.queue == "discarded" for item in steps),
        generated_messages=len(batch.overlays),
        summary_draft_id=summary.draft.draft_id,
        steps=steps,
        highlights=clips,
    )
    simulation_store.save(report)
    return report
