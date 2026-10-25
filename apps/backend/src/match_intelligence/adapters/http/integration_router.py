from pathlib import Path
import os
from contextlib import asynccontextmanager
import asyncio

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.integrated_pipeline import (
    IntegratedPipeline,
    PipelineArtifactError,
    PipelinePaths,
)
from match_intelligence.application.realtime_observations import (
    LiveObservation,
    RealtimeObservationHub,
)
from match_intelligence.application.observation_playback import (
    ObservationPlaybackSession,
    load_playback_observations,
)
from match_intelligence.application.vision_runtime import (
    VisionObservationRuntime,
    VisionRuntimeSettings,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
pipeline = IntegratedPipeline(PipelinePaths.from_repository(REPOSITORY_ROOT))
live_hub = RealtimeObservationHub()
vision_runtime = VisionObservationRuntime(
    live_hub,
    VisionRuntimeSettings.from_environment(),
)
observation_playback: ObservationPlaybackSession | None = None


def get_observation_playback() -> ObservationPlaybackSession:
    global observation_playback
    if observation_playback is None:
        observation_playback = ObservationPlaybackSession(
            load_playback_observations(pipeline),
            vision_runtime,
        )
    return observation_playback

router = APIRouter(prefix="/api/v1/integration", tags=["Integración de datos y visión"])


class LiveObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1, max_length=160)
    source: Literal["roboflow", "soccernet", "fusion", "synthetic-replay"]
    kind: Literal["spatial_detection", "temporal_action", "fusion_candidate"]
    timestamp_ms: int = Field(ge=0)
    payload: dict[str, Any]


class PlaybackPositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_time_ms: int = Field(ge=0)


@asynccontextmanager
async def integration_lifespan(_: object):
    await start_integration_runtime()
    try:
        yield
    finally:
        await close_integration_runtime()


async def start_integration_runtime() -> None:
    await vision_runtime.start()


async def close_integration_runtime() -> None:
    await vision_runtime.close()


@router.get("/status")
async def integration_status() -> dict[str, object]:
    try:
        result = pipeline.status()
        transport = os.getenv("EVENT_TRANSPORT", "memory")
        result["runtime"] = {
            "event_transport": transport,
            "event_hubs_configured": all(
                os.getenv(name)
                for name in (
                    "EVENT_HUB_FULLY_QUALIFIED_NAMESPACE",
                    "EVENT_HUB_NAME",
                    "EVENT_HUB_CONSUMER_GROUP",
                )
            ),
            "blob_storage_configured": bool(
                os.getenv("AZURE_BLOB_SERVICE_ENDPOINT")
            ),
            "credentials_present": all(
                os.getenv(name)
                for name in (
                    "AZURE_TENANT_ID",
                    "AZURE_CLIENT_ID",
                    "AZURE_CLIENT_SECRET",
                )
            ),
            "vision_observations": vision_runtime.status(),
        }
        return result
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/timeline")
async def integration_timeline(
    start_ms: int = Query(ge=0),
    end_ms: int = Query(ge=0),
    spatial_limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    try:
        return pipeline.timeline(
            start_ms=start_ms,
            end_ms=end_ms,
            spatial_limit=spatial_limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/observations", status_code=202)
async def ingest_live_observation(item: LiveObservationRequest) -> dict[str, object]:
    observation = LiveObservation(
        observation_id=item.observation_id,
        source=item.source,
        kind=item.kind,
        timestamp_ms=item.timestamp_ms,
        payload=item.payload,
        received_at=datetime.now(UTC),
    )
    accepted = await vision_runtime.publish(observation)
    return {"accepted": accepted, "duplicate": not accepted}


@router.get("/live/status")
async def live_status() -> dict[str, object]:
    try:
        playback = get_observation_playback().snapshot()
    except PipelineArtifactError as error:
        playback = {"status": "unavailable", "detail": str(error)}
    return {**live_hub.snapshot(), "playback": playback}


@router.post("/live/playback/play")
async def playback_play(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        return await get_observation_playback().play(position.video_time_ms)
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/pause")
async def playback_pause(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        return await get_observation_playback().pause(position.video_time_ms)
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/advance")
async def playback_advance(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        return await get_observation_playback().advance(position.video_time_ms)
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/seek")
async def playback_seek(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        return await get_observation_playback().seek(position.video_time_ms)
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/restart")
async def playback_restart() -> dict[str, object]:
    live_hub.clear()
    try:
        return await get_observation_playback().restart()
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.websocket("/live/ws")
async def live_observations(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = live_hub.subscribe()
    try:
        await websocket.send_json({"type": "status", **live_hub.snapshot()})
        while True:
            observation_task = asyncio.create_task(queue.get())
            disconnect_task = asyncio.create_task(websocket.receive())
            done, pending = await asyncio.wait(
                {observation_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if disconnect_task in done:
                message = disconnect_task.result()
                if message["type"] == "websocket.disconnect":
                    break
                continue
            observation = observation_task.result()
            await websocket.send_json(
                {"type": "observation", "observation": observation.as_dict()}
            )
    except WebSocketDisconnect:
        pass
    finally:
        live_hub.unsubscribe(queue)
