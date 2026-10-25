"""API y página aisladas para comprobar VideoSynchronizedReplay con un MP4 real."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.video_sync import (
    SynchronizedEvent,
    VideoSynchronizedReplay,
)
from match_intelligence.adapters.http.integration_router import (
    integration_lifespan,
    pipeline,
    router as integration_router,
)
from match_intelligence.domain.contracts import MatchEvent


EXPERIMENT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIRECTORY.parents[1]
STATIC_DIRECTORY = EXPERIMENT_DIRECTORY / "static"
VIDEO_PATH = Path(
    os.getenv(
        "MENTOX_INTEGRATION_VIDEO",
        str(REPOSITORY_ROOT / "experiments/authorized-video/input/2e57b9_0.mp4"),
    )
)


class PositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_time_ms: int = Field(ge=0, le=30_000)


class DiagnosticPublisher:
    def __init__(self) -> None:
        self.visible_events: list[dict[str, Any]] = []

    async def publish(self, synchronized: SynchronizedEvent) -> None:
        self.visible_events.append(serialize_event(synchronized.event))

    def clear(self) -> None:
        self.visible_events.clear()


class DiagnosticRebuilder:
    def __init__(self) -> None:
        self.events: tuple[MatchEvent, ...] = ()
        self.video_time_ms = 0

    async def rebuild(
        self,
        events: tuple[MatchEvent, ...],
        *,
        video_time_ms: int,
    ) -> None:
        self.events = events
        self.video_time_ms = video_time_ms


def diagnostic_events() -> tuple[MatchEvent, ...]:
    raw_events = (
        ("evt-pass-005", 5_000, "pass", "success", "team-red", "player-3"),
        ("evt-recovery-010", 10_000, "recovery", "success", "team-blue", "player-6"),
        ("evt-pass-015", 15_000, "pass", "success", "team-red", "player-9"),
        ("evt-possession-020", 20_000, "possession_change", "success", "team-blue", None),
        ("evt-pressure-025", 25_000, "pressure", "unknown", "team-red", "player-9"),
    )
    return tuple(
        MatchEvent(
            schema_version="1.0",
            event_id=event_id,
            match_id="grf-dv-us-17",
            period=1,
            clock_ms=video_time_ms,
            video_time_ms=video_time_ms,
            type=event_type,
            team_id=team_id,
            player_id=player_id,
            outcome=outcome,
            source="synthetic",
        )
        for event_id, video_time_ms, event_type, outcome, team_id, player_id in raw_events
    )


def serialize_event(event: MatchEvent) -> dict[str, Any]:
    result = event.model_dump(mode="json")
    result.update(
        {
            "timing_basis": "provided_event_timestamp",
            "prediction_origin": "manual_alignment",
            "track_id": None,
            "identity_status": (
                "provided_synthetic_identity"
                if event.player_id is not None
                else "identity_unavailable"
            ),
        }
    )
    return result


class DiagnosticSession:
    def __init__(self) -> None:
        self.events = diagnostic_events()
        self.publisher = DiagnosticPublisher()
        self.rebuilder = DiagnosticRebuilder()
        self.replay = VideoSynchronizedReplay(
            self.events,
            self.publisher,
            self.rebuilder,
        )
        self.log: list[dict[str, Any]] = []

    def record(self, action: str, **details: Any) -> None:
        self.log.append(
            {
                "recorded_at": datetime.now(UTC).isoformat(),
                "action": action,
                "video_time_ms": self.replay.video_time_ms,
                **details,
            }
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "match_id": "grf-dv-us-17",
            "playback_state": self.replay.state.value,
            "video_time_ms": self.replay.video_time_ms,
            "current_time_seconds": self.replay.video_time_ms / 1_000,
            "event_cursor": self.replay.position,
            "total_events": len(self.events),
            "visible_events": self.publisher.visible_events,
            "reconstructed_state": {
                "event_count": len(self.rebuilder.events),
                "event_ids": [event.event_id for event in self.rebuilder.events],
                "video_time_ms": self.rebuilder.video_time_ms,
            },
            "timing_basis": "provided_event_timestamp",
            "detection_status": "not_automatic_detection",
        }


session_lock = asyncio.Lock()
session = DiagnosticSession()

app = FastAPI(
    title="Mentox Video Sync Diagnostic",
    version="1.0.0",
    description="Aplicación aislada de DV-US-18; no es la API pública del producto.",
    lifespan=integration_lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
app.include_router(integration_router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/media/integration-video.mp4", include_in_schema=False)
def video() -> FileResponse:
    if not VIDEO_PATH.is_file():
        raise HTTPException(
            status_code=404,
            detail="Coloque el vídeo autorizado o defina MENTOX_INTEGRATION_VIDEO",
        )
    return FileResponse(VIDEO_PATH, media_type="video/mp4")


@app.post("/api/integration/video-sync/session")
async def create_session() -> dict[str, Any]:
    global session
    async with session_lock:
        session = DiagnosticSession()
        session.record("session_created")
        return session.snapshot()


@app.get("/api/integration/video-sync/session")
async def get_session() -> dict[str, Any]:
    async with session_lock:
        return session.snapshot()


@app.post("/api/integration/video-sync/play")
async def play() -> dict[str, Any]:
    async with session_lock:
        session.replay.play()
        session.record("play")
        return session.snapshot()


@app.post("/api/integration/video-sync/pause")
async def pause() -> dict[str, Any]:
    async with session_lock:
        session.replay.pause()
        session.record("pause")
        return session.snapshot()


@app.post("/api/integration/video-sync/advance")
async def advance(position: PositionRequest) -> dict[str, Any]:
    async with session_lock:
        delivered = await session.replay.advance_to(position.video_time_ms)
        session.record(
            "advance",
            delivered_event_ids=[item.event.event_id for item in delivered],
        )
        return session.snapshot()


@app.post("/api/integration/video-sync/seek")
async def seek(position: PositionRequest) -> dict[str, Any]:
    async with session_lock:
        history = await session.replay.seek(position.video_time_ms)
        session.publisher.clear()
        session.record(
            "seek",
            reconstructed_event_ids=[event.event_id for event in history],
            visible_history_republished=False,
        )
        return session.snapshot()


@app.post("/api/integration/video-sync/restart")
async def restart() -> dict[str, Any]:
    async with session_lock:
        await session.replay.restart()
        session.publisher.clear()
        session.record("restart", visible_history_republished=False)
        return session.snapshot()


@app.get("/api/integration/video-sync/log")
async def export_log() -> dict[str, Any]:
    async with session_lock:
        return {
            "schema_version": "1.0",
            "experiment": "DV-US-18",
            "contains_sensitive_data": False,
            "session": session.snapshot(),
            "records": session.log,
        }
