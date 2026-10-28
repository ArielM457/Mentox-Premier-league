from pathlib import Path
import os
from contextlib import asynccontextmanager
import asyncio

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient
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
from match_intelligence.application.live_vision_capture import (
    CaptureNotPlayingError,
    CaptureUnavailableError,
    LiveVisionCapture,
    LiveVisionSettings,
    RoboflowSuitePredictor,
)
from match_intelligence.application.teamspotting_analysis import (
    TeamSpottingAnalysis,
    TeamSpottingSettings,
    TeamSpottingUnavailableError,
)
from match_intelligence.application.gamestate_analysis import (
    GameStateAnalysis,
    GameStateSettings,
    GameStateUnavailableError,
)
from match_intelligence.adapters.http.registry import get_registry
from match_intelligence.application.match_session import NotFoundError
from match_intelligence.application.simulated_video import SimulatedVideo
from match_intelligence.application.model_http import wait_for_model
from match_intelligence.adapters.http.routing_router import routing_pipeline


REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
pipeline = IntegratedPipeline(PipelinePaths.from_repository(REPOSITORY_ROOT))
live_hub = RealtimeObservationHub()
vision_runtime = VisionObservationRuntime(
    live_hub,
    VisionRuntimeSettings.from_environment(),
)
live_vision_settings = LiveVisionSettings.from_environment()
live_vision_capture = LiveVisionCapture(
    RoboflowSuitePredictor(live_vision_settings),
    vision_runtime,
    live_vision_settings,
)
teamspotting_analysis = TeamSpottingAnalysis(
    vision_runtime,
    TeamSpottingSettings.from_environment(),
)
gamestate_analysis = GameStateAnalysis(vision_runtime, (
    GameStateSettings.from_environment()
    if os.getenv("SOCCERNET_GAMESTATE_ENABLED", "false").lower() in {"true", "1", "yes"}
    else GameStateSettings(None, None, None, "synthetic-videos", None)
))
simulated_video = SimulatedVideo()


def _gamestate_enabled() -> bool:
    # GameState retirado: los exports viejos no deben reactivar su dependencia.
    return os.getenv("SOCCERNET_GAMESTATE_ENABLED", "false").lower() in {"true", "1", "yes"}


def _temporal_predictions():
    if simulated_video.replay is not None and teamspotting_analysis.status().get("media_sha256") != simulated_video.replay.media_sha256:
        return ()
    return teamspotting_analysis.predictions


async def _simulator_control(action: str, position: "PlaybackPositionRequest") -> int | None:
    try:
        return await simulated_video.control(action, position.match_id, position.video_time_ms,
                                             vision_runtime, routing_pipeline, _temporal_predictions(),
                                             generation=position.playback_generation, temporal=teamspotting_analysis)
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"No se pudieron entregar los eventos del simulador: {error}") from error
observation_playback: ObservationPlaybackSession | None = None
# Cada respuesta parcial del vídeo lleva como máximo esto; el navegador pide la parte siguiente.
VIDEO_RANGE_MAX_BYTES = 4 * 1024 * 1024
model_preparation_task: asyncio.Task[dict[str, object]] | None = None
model_preparation_status: dict[str, object] = {
    "status": "idle",
    "match_id": None,
    "error": None,
}


def get_observation_playback() -> ObservationPlaybackSession:
    global observation_playback
    if observation_playback is None:
        # Los artefactos locales son de otro vídeo; nunca se reproducen sobre Blob.
        use_blob = bool(os.getenv("AZURE_BLOB_SERVICE_ENDPOINT") and os.getenv("VISION_VIDEO_BLOB_NAME"))
        observation_playback = ObservationPlaybackSession(
            () if use_blob else load_playback_observations(pipeline),
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
    match_id: str = Field(default="demo", min_length=1, max_length=160)
    playback_generation: int | None = Field(default=None, ge=0)


@asynccontextmanager
async def integration_lifespan(_: object):
    await start_integration_runtime()
    try:
        yield
    finally:
        await close_integration_runtime()


async def start_integration_runtime() -> None:
    await vision_runtime.start()
    if simulated_video.configured:
        try:
            await simulated_video.prepare(os.getenv("VISION_STARTUP_MATCH_ID", "synthetic-live-001"), get_registry())
        except ValueError:
            # API diagnóstica disponible; Play mostrará el error y no mezclará partidos.
            pass
    if _prepare_on_startup():
        _start_model_preparation(os.getenv("VISION_STARTUP_MATCH_ID", "synthetic-live-001"))


async def close_integration_runtime() -> None:
    global model_preparation_task
    if model_preparation_task is not None and not model_preparation_task.done():
        model_preparation_task.cancel()
        await asyncio.gather(model_preparation_task, return_exceptions=True)
    model_preparation_task = None
    await live_vision_capture.close()
    await teamspotting_analysis.close()
    await gamestate_analysis.close()
    await vision_runtime.close()


@router.get("/status")
async def integration_status() -> dict[str, object]:
    try:
        try:
            if simulated_video.configured:
                simulator = simulated_video.status()
                result = {
                    "status": model_preparation_status.get("status", "idle") if simulator["status"] == "ready" else simulator["status"],
                    "artifact_scope": "current_blob_video",
                    "match_id": simulated_video.match_id,
                    "media_sha256": simulator["media_sha256"],
                    "video_available": simulated_video.video_bytes is not None,
                    "duration_ms": simulated_video.replay.duration_ms if simulated_video.replay else None,
                    "roboflow": live_vision_capture.status(simulated_video.match_id),
                    "soccernet": teamspotting_analysis.status(),
                    "fusion": {"status": "synthetic_reference_with_unverified_model_candidates",
                               "events_available": simulator["events"], "match_events_routed": simulator["events_routed"]},
                }
            else:
                result = pipeline.status()
                result["artifact_scope"] = "historical_local_video_only"
        except PipelineArtifactError as error:
            result = {
                "status": "historical_artifacts_unavailable",
                "artifact_error": str(error),
                "fusion": {"match_events_published": 0, "status": "not_available"},
            }
        result.setdefault("artifact_scope", "historical_local_video_only")
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
            "live_capture": live_vision_capture.status(),
            "teamspotting": teamspotting_analysis.status(),
            "gamestate": gamestate_analysis.status() if _gamestate_enabled() else {"configured": False, "status": "retired"},
            "simulator": simulated_video.status(),
            "model_preparation": dict(model_preparation_status),
            "video_source": {
                "configured": bool(
                    os.getenv("AZURE_BLOB_SERVICE_ENDPOINT")
                    and os.getenv("VISION_VIDEO_BLOB_NAME")
                ),
                "container": os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos"),
            },
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
    return {
        **live_hub.snapshot(),
        "playback": playback,
        "capture": live_vision_capture.status(),
    }


@router.get("/live/observations")
async def observations_in_window(
    match_id: str = Query(min_length=1, max_length=160),
    start_ms: int = Query(ge=0),
    end_ms: int = Query(ge=0),
    limit: int = Query(default=1000, ge=1, le=5000),
) -> dict[str, object]:
    if end_ms < start_ms:
        raise HTTPException(status_code=422, detail="end_ms debe ser mayor o igual a start_ms")
    observations = live_hub.observations_between(
        match_id=match_id, start_ms=start_ms, end_ms=end_ms, limit=limit
    )
    observations.extend(item.as_dict() for item in teamspotting_analysis.observations_between(match_id, start_ms, end_ms))
    observations.extend(item.as_dict() for item in simulated_video.observations(match_id, start_ms, end_ms, _temporal_predictions()))
    unique = {(item["source"], item["observation_id"]): item for item in observations}
    return {
        "match_id": match_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "observations": sorted(unique.values(), key=lambda item: (item["timestamp_ms"], item["observation_id"]))[-limit:],
    }


@router.get("/live/analytics")
async def live_video_analytics(
    match_id: str = Query(default="synthetic-live-001", min_length=1, max_length=160),
    until_video_ms: int | None = Query(default=None, ge=0),
) -> dict[str, object]:
    """Métricas causales del simulador; GameState solo mediante opt-in explícito."""
    if not _gamestate_enabled():
        return {"match_id": match_id, "until_video_ms": until_video_ms,
                **simulated_video.analytics(match_id, until_video_ms)}
    available = gamestate_analysis.match_id == match_id and bool(
        gamestate_analysis.tracking_frames
    )
    return {
        "match_id": match_id,
        "source": "soccernet-gamestate",
        "status": "ready" if available else "not_available",
        "tracking_frames": len(gamestate_analysis.tracking_frames) if available else 0,
        "until_video_ms": until_video_ms,
        "metrics": list(gamestate_analysis.metrics_until(until_video_ms)) if available else [],
        "limitations": [
            "La identidad nominal solo se confirma por equipo, dorsal y plantilla verificada.",
            "GameState no aporta una trayectoria de balón; velocidad de balón y tiro permanecen no disponibles.",
        ],
    }


def _video_match(match_id: str = Query(min_length=1, max_length=160)) -> str:
    """Solo el partido con vídeo se prepara: despertar los modelos cuesta y su estado es compartido.

    Así nadie puede encender la GPU con otro partido ni dejar el del vídeo esperando un 409.
    """
    if match_id != os.getenv("VISION_STARTUP_MATCH_ID", "synthetic-live-001"):
        raise HTTPException(status_code=404, detail="Este partido no tiene vídeo para preparar")
    return match_id


@router.post("/live/models/prepare")
async def prepare_live_models(match_id: Annotated[str, Depends(_video_match)]) -> dict[str, object]:
    """Despierta el servicio de visión y no habilita Play hasta que esté listo."""
    try:
        # Una desconexión del navegador no debe cancelar la inferencia compartida.
        return await asyncio.shield(_start_model_preparation(match_id))
    except HTTPException:
        raise
    except (
        CaptureUnavailableError,
        TeamSpottingUnavailableError,
        GameStateUnavailableError,
    ) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"No se pudieron preparar los modelos: {error}") from error


def _prepare_on_startup() -> bool:
    requested = os.getenv("VISION_PREPARE_ON_STARTUP", "true").strip().lower()
    return requested not in {"0", "false", "no", "off"} and any(
        (
            live_vision_settings.endpoint,
            teamspotting_analysis.settings.endpoint,
            gamestate_analysis.settings.endpoint if _gamestate_enabled() else None,
            simulated_video.configured,
        )
    )


def _start_model_preparation(match_id: str) -> asyncio.Task[dict[str, object]]:
    """Inicia una sola preparación y comparte la tarea con Play y el arranque."""
    global model_preparation_task
    if model_preparation_task is not None and not model_preparation_task.done():
        if model_preparation_status.get("match_id") != match_id:
            raise HTTPException(status_code=409, detail="Ya se está preparando otro partido")
        return model_preparation_task
    # Al reanudar se comprueba salud otra vez: Container Apps pudo escalar
    # a cero durante la pausa. Los clientes conservan sus resultados, por
    # lo que esto no repite la inferencia del MP4.
    if model_preparation_task is None or model_preparation_task.done():
        model_preparation_status.update(status="preparing", match_id=match_id, error=None, models={})
        model_preparation_task = asyncio.create_task(_prepare_models(match_id))
        model_preparation_task.add_done_callback(_observe_model_preparation)
    return model_preparation_task


def _observe_model_preparation(task: asyncio.Task[dict[str, object]]) -> None:
    """Recupera la excepción de tareas de arranque para evitar errores silenciosos."""
    if not task.cancelled():
        task.exception()


async def _prepare_models(match_id: str) -> dict[str, object]:
    model_preparation_status.update(status="preparing", match_id=match_id, error=None)
    try:
        simulator = await simulated_video.prepare(match_id, get_registry())
        if simulated_video.video_bytes is not None and isinstance(teamspotting_analysis, TeamSpottingAnalysis):
            teamspotting_analysis.bind_video(simulated_video.video_bytes)
        try:
            session = get_registry().get(match_id)
            metadata = session.metadata
        except NotFoundError:
            session = None
            metadata = None
        async def prepare_one(name: str, operation: Any) -> dict[str, object]:
            states = model_preparation_status.setdefault("models", {})
            states[name] = {"status": "preparing"}
            try:
                result = await operation
                states[name] = result
                return result
            except Exception as error:
                states[name] = {"status": "failed", "error": str(error)}
                raise

        async def prepare_roboflow() -> dict[str, object]:
            if not live_vision_settings.endpoint:
                return {"status": "disabled", "configured": False}
            return await wait_for_model(live_vision_capture.ensure_ready)

        async def prepare_gamestate():
            if not _gamestate_enabled():
                return {"status": "retired", "configured": False}
            return await gamestate_analysis.prepare(match_id, metadata)

        results = await asyncio.gather(
            prepare_one("roboflow", prepare_roboflow()),
            prepare_one("teamspotting", teamspotting_analysis.prepare(match_id)),
            prepare_one("gamestate", prepare_gamestate()),
            return_exceptions=True,
        )
        errors = [item for item in results if isinstance(item, BaseException)]
        if errors:
            raise GameStateUnavailableError("; ".join(str(error) for error in errors))
        roboflow, teamspotting, gamestate = results
        if simulator.get("status") == "ready" and any(item.get("status") != "ready" for item in (roboflow, teamspotting)):
            raise CaptureUnavailableError("Para analizar este vídeo configure Roboflow Suite y TeamSpotting en el backend")
        hashes = {item.get("media_sha256") for item in (teamspotting, gamestate, simulator) if item.get("media_sha256")}
        if len(hashes) > 1:
            raise GameStateUnavailableError("Los modelos y el simulador procesaron vídeos diferentes; revise Blob Storage")
        if _gamestate_enabled() and session is not None and gamestate_analysis.tracking_frames:
            session.set_tracking_frames(gamestate_analysis.tracking_frames)
        result = {
            "status": "ready",
            "models": {
                "roboflow": roboflow,
                "teamspotting": teamspotting,
                "gamestate": gamestate,
            },
            "capture": live_vision_capture.status(),
            "simulator": simulator,
        }
        model_preparation_status.update(status="ready", error=None)
        return result
    except asyncio.CancelledError:
        model_preparation_status.update(status="interrupted", error="El backend se detuvo durante la preparación")
        raise
    except Exception as error:
        model_preparation_status.update(status="failed", error=str(error))
        raise


@router.post("/live/playback/play")
async def playback_play(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        if simulated_video.configured and position.match_id == os.getenv("VISION_STARTUP_MATCH_ID", "synthetic-live-001") and simulated_video.phase != "ready":
            raise HTTPException(status_code=503, detail=simulated_video.error or "Preparando los datos del vídeo simulado")
        if simulated_video.match_id == position.match_id and (
            model_preparation_status.get("status") != "ready" or model_preparation_status.get("match_id") != position.match_id
        ):
            raise HTTPException(status_code=503, detail="Los modelos de este vídeo todavía no están preparados")
        generation = await _simulator_control("play", position)
        live_vision_capture.play(position.match_id)
        playback = await get_observation_playback().play(position.video_time_ms)
        return {**playback, "capture": live_vision_capture.status(position.match_id), "playback_generation": generation}
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/pause")
async def playback_pause(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        live_vision_capture.pause(position.match_id)
        simulated_video.halt(position.match_id)
        await _simulator_control("pause", position)
        playback = await get_observation_playback().pause(position.video_time_ms)
        return {**playback, "capture": live_vision_capture.status(position.match_id)}
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/advance")
async def playback_advance(position: PlaybackPositionRequest) -> dict[str, object]:
    problem = simulated_video.advance_problem(position.match_id, position.video_time_ms, position.playback_generation)
    if problem:
        raise HTTPException(status_code=409, detail=problem)
    try:
        await _simulator_control("advance", position)
        return await get_observation_playback().advance(position.video_time_ms)
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/seek")
async def playback_seek(position: PlaybackPositionRequest) -> dict[str, object]:
    try:
        live_vision_capture.seek(position.match_id)
        generation = await _simulator_control("seek", position)
        return {**await get_observation_playback().seek(position.video_time_ms), "playback_generation": generation}
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/live/playback/restart")
async def playback_restart(
    position: PlaybackPositionRequest | None = None,
) -> dict[str, object]:
    live_hub.clear()
    live_vision_capture.restart(position.match_id if position else "demo")
    await simulated_video.control("restart", position.match_id if position else "demo", 0, vision_runtime, routing_pipeline, _temporal_predictions())
    try:
        return await get_observation_playback().restart()
    except PipelineArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/live/video")
async def live_video(request: Request) -> Response:
    """Sirve un MP4 privado de Blob Storage por partes, sin cargarlo entero en memoria."""
    endpoint = os.getenv("AZURE_BLOB_SERVICE_ENDPOINT")
    blob_name = os.getenv("VISION_VIDEO_BLOB_NAME")
    container = os.getenv("VISION_VIDEO_CONTAINER", "synthetic-videos")
    if not endpoint or not blob_name:
        raise HTTPException(status_code=404, detail="No hay un vídeo de Blob Storage configurado")

    if simulated_video.configured:
        if simulated_video.phase != "ready" or simulated_video.video_bytes is None:
            raise HTTPException(status_code=503, detail=simulated_video.error or "Cargando los datos del vídeo simulado")
        # Snapshot inmutable validado por hash: vídeo y eventos no cambian
        # entre rangos ni requieren transferencias repetidas a Blob.
        return video_response(simulated_video.video_bytes, request.headers.get("range"), simulated_video.replay.media_sha256)

    credential = DefaultAzureCredential()
    service = BlobServiceClient(account_url=endpoint, credential=credential)

    async def close() -> None:
        await service.close()
        await credential.close()

    try:
        blob = service.get_blob_client(container=container, blob=blob_name)
        properties = await blob.get_blob_properties()
        if simulated_video.configured:
            if simulated_video.phase != "ready":
                raise HTTPException(status_code=503, detail=simulated_video.error or "Cargando los datos del vídeo simulado")
            if simulated_video.video_etag != properties.etag:
                raise HTTPException(status_code=409, detail="El vídeo cambió después de cargar sus eventos; reinicie la preparación")
        total = properties.size
        start, end = 0, total - 1
        range_header = request.headers.get("range")
        status_code = 200
        if range_header:
            try:
                unit, value = range_header.split("=", 1)
                first, last = value.split("-", 1)
                if unit != "bytes" or not first:
                    raise ValueError
                start = int(first)
                end = min(int(last) if last else total - 1, total - 1, start + VIDEO_RANGE_MAX_BYTES - 1)
                if start < 0 or start > end:
                    raise ValueError
                status_code = 206
            except ValueError as error:
                raise HTTPException(status_code=416, detail="Rango de vídeo inválido") from error
        downloader = await blob.download_blob(offset=start, length=end - start + 1)
    except BaseException:
        await close()
        raise

    # Sin rango, el archivo completo también se envía por bloques: nunca queda entero en memoria.
    async def body():
        try:
            async for chunk in downloader.chunks():
                yield chunk
        finally:
            await close()

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Cache-Control": "private, max-age=60",
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
    return StreamingResponse(body(), status_code=status_code, media_type="video/mp4", headers=headers)


async def _read_frame(request: Request, limit: int) -> bytes:
    """Lee el fotograma por partes y corta en cuanto supera ``limit``, sin cargarlo entero."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail="El fotograma supera el límite permitido")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(status_code=413, detail="El fotograma supera el límite permitido")
        chunks.append(chunk)
    return b"".join(chunks)


def video_response(content: bytes, range_header: str | None, media_hash: str) -> Response:
    total = len(content)
    start, end = 0, total - 1
    if range_header:
        try:
            unit, value = range_header.split("=", 1)
            first, last = value.split("-", 1)
            if unit != "bytes" or "," in value or total == 0:
                raise ValueError
            if first:
                start = int(first)
                end = min(int(last), total - 1) if last else total - 1
            else:
                length = int(last)
                if length <= 0:
                    raise ValueError
                start, end = max(0, total - length), total - 1
            if not 0 <= start <= end < total:
                raise ValueError
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=416, detail="Rango de vídeo inválido",
                                headers={"Content-Range": f"bytes */{total}"}) from error
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, no-cache", "ETag": f'"{media_hash}"'}
    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
    return Response(content[start:end + 1], status_code=206 if range_header else 200,
                    media_type="video/mp4", headers=headers)


@router.post("/live/capture/frame", status_code=202)
async def capture_live_frame(
    request: Request,
    match_id: str = Query(min_length=1, max_length=160),
    video_time_ms: int = Query(ge=0),
) -> dict[str, object]:
    """Recibe el fotograma visible; la credencial del modelo nunca sale del backend."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    try:
        # Pausa y tipo se comprueban antes de leer el cuerpo, que nunca supera el límite.
        live_vision_capture.ensure_accepting(match_id, content_type)
        image = await _read_frame(request, live_vision_capture.settings.max_image_bytes)
        return await live_vision_capture.capture(
            match_id=match_id,
            video_time_ms=video_time_ms,
            image=image,
            content_type=content_type,
        )
    except CaptureNotPlayingError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except CaptureUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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
