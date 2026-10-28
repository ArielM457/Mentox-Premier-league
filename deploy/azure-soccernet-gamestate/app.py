"""API asíncrona para SoccerNet Game State Reconstruction."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hmac import compare_digest
import json
import math
import os
import re
import signal
from pathlib import Path
import shutil
from typing import Annotated, Any, Optional
from uuid import uuid4

import cv2
from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
import torch


API_KEY = os.getenv("MENTOX_MODEL_API_KEY", "")
ROOT = Path(os.getenv("MENTOX_GAMESTATE_WORK_DIR", "/work/analyses"))
MAX_VIDEO_BYTES = int(os.getenv("MENTOX_MAX_VIDEO_BYTES", str(256 * 1024 * 1024)))
MAX_VIDEO_SECONDS = float(os.getenv("MENTOX_MAX_VIDEO_SECONDS", "240"))
FRAME_LIMIT = int(os.getenv("MENTOX_GAMESTATE_FRAME_LIMIT", "0"))
LOW_VRAM = os.getenv("MENTOX_GAMESTATE_LOW_VRAM", "0")
RUNNER = Path("/opt/prime/run_analysis.sh")
MODEL_MANIFEST = Path("/models/preloaded-models.json")
ANALYSIS_TIMEOUT_SECONDS = float(os.getenv("MENTOX_GAMESTATE_ANALYSIS_TIMEOUT_SECONDS", "3600"))


def inspect_preloaded_models() -> dict[str, Any]:
    if not MODEL_MANIFEST.is_file():
        raise RuntimeError("Falta el manifiesto de pesos precargados")
    manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    models = manifest.get("models", [])
    expected = {
        "reid-soccernet", "reid-hrnet32", "pitch-keypoints", "pitch-lines",
        "bbox-yolo11m", "jersey-ocr-detector", "jersey-ocr-recognizer",
    }
    if {model.get("name") for model in models} != expected:
        raise RuntimeError("El manifiesto debe contener los siete pesos requeridos")
    missing = []
    for model in models:
        path = Path(model["path"])
        if not path.is_file() or path.stat().st_size != model["bytes"]:
            missing.append(model["name"])
    if missing:
        raise RuntimeError(f"Pesos ausentes o incompletos: {', '.join(missing)}")
    return {"count": len(models), "names": [model["name"] for model in models]}


def require_api_key(supplied: Annotated[Optional[str], Header(alias="X-API-Key")] = None) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="MENTOX_MODEL_API_KEY no está configurada")
    if supplied is None or not compare_digest(supplied, API_KEY):
        raise HTTPException(status_code=401, detail="Credencial de inferencia inválida")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def metadata_path(analysis_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", analysis_id):
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return ROOT / analysis_id / "status.json"


def read_metadata(analysis_id: str) -> dict[str, Any]:
    path = metadata_path(analysis_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return json.loads(path.read_text(encoding="utf-8"))


def write_metadata(analysis_id: str, data: dict[str, Any]) -> None:
    path = metadata_path(analysis_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def inspect_video(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("OpenCV no pudo abrir el MP4")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()
    if not math.isfinite(fps) or fps <= 0 or frames <= 0 or width <= 0 or height <= 0:
        raise ValueError("El MP4 no informa FPS o cuadros válidos")
    duration = frames / fps
    if duration > MAX_VIDEO_SECONDS:
        raise ValueError(f"El video dura {duration:.2f}s; el máximo es {MAX_VIDEO_SECONDS:.0f}s")
    return {"fps": fps, "frames": frames, "duration_ms": round(duration * 1000), "width": width, "height": height}


async def execute_analysis(analysis_id: str) -> None:
    directory = ROOT / analysis_id
    metadata = read_metadata(analysis_id)
    environment = os.environ.copy()
    environment.update({
        "MENTOX_GAMESTATE_VIDEO_PATH": str(directory / "input.mp4"),
        "MENTOX_GAMESTATE_OUTPUT_DIR": str(directory / "output"),
        "MENTOX_GAMESTATE_FRAME_LIMIT": str(FRAME_LIMIT),
        "MENTOX_GAMESTATE_LOW_VRAM": LOW_VRAM,
    })
    log_path = directory / "analysis.log"
    process = None
    try:
        async with app.state.analysis_lock:
            metadata.update({"status": "running", "started_at": utc_now()})
            write_metadata(analysis_id, metadata)
            with log_path.open("wb") as log:
                process = await asyncio.create_subprocess_exec(
                    str(RUNNER),
                    env=environment,
                    stdout=log,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
                return_code = await asyncio.wait_for(process.wait(), timeout=ANALYSIS_TIMEOUT_SECONDS)
        if return_code != 0:
            raise RuntimeError(f"GameState terminó con código {return_code}")
        result = directory / "output" / "gamestate-observations.jsonl"
        with result.open("r", encoding="utf-8") as source:
            observations = sum(1 for line in source if line.strip())
        metadata.update({
            "status": "succeeded",
            "finished_at": utc_now(),
            "observations": observations,
            "result_path": f"/v1/analyses/{analysis_id}/result",
        })
    except asyncio.TimeoutError:
        metadata.update({"status": "failed", "finished_at": utc_now(),
                         "error": f"GameState superó {ANALYSIS_TIMEOUT_SECONDS:g} segundos"})
    except asyncio.CancelledError:
        metadata.update({"status": "failed", "finished_at": utc_now(),
                         "error": "El servicio se detuvo durante el análisis"})
        raise
    except Exception as error:  # el detalle completo permanece en analysis.log
        metadata.update({"status": "failed", "finished_at": utc_now(), "error": str(error)})
    finally:
        if process is not None and process.returncode is None:
            # TrackLab crea otros procesos; terminar todo el grupo libera la GPU.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()
        write_metadata(analysis_id, metadata)
        (directory / "input.mp4").unlink(missing_ok=True)
        app.state.accepting_analysis = False


async def startup() -> None:
    if not API_KEY:
        raise RuntimeError("MENTOX_MODEL_API_KEY es obligatoria")
    if not math.isfinite(ANALYSIS_TIMEOUT_SECONDS) or ANALYSIS_TIMEOUT_SECONDS <= 0:
        raise RuntimeError("MENTOX_GAMESTATE_ANALYSIS_TIMEOUT_SECONDS debe ser positivo")
    ROOT.mkdir(parents=True, exist_ok=True)
    app.state.preloaded_models = inspect_preloaded_models()
    app.state.analysis_lock = asyncio.Lock()
    app.state.accepting_analysis = False
    # El disco de una réplica no permite reanudar un proceso tras un reinicio.
    for path in ROOT.glob("*/status.json"):
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("status") in {"queued", "running"}:
            saved.update(status="failed", finished_at=utc_now(), error="Réplica reiniciada durante el análisis")
            write_metadata(path.parent.name, saved)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await startup()
    yield


app = FastAPI(title="The Prime Moment SoccerNet GameState", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> dict[str, Any]:
    if not RUNNER.is_file() or not torch.cuda.is_available():
        raise HTTPException(status_code=503, detail="GameState o CUDA todavía no están listos")
    return {
        "status": "ready",
        "model": "SoccerNet GameState Reconstruction",
        "device": torch.cuda.get_device_name(0),
        "mode": "asynchronous",
        "weights": app.state.preloaded_models,
    }


@app.post("/v1/analyses", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_api_key)])
async def create_analysis(
    background_tasks: BackgroundTasks,
    video: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    if video.content_type not in {"video/mp4", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Use un video MP4")
    # En una réplica con disco efímero no hay una cola durable: el cliente reintenta.
    if getattr(app.state, "accepting_analysis", False):
        raise HTTPException(status_code=429, detail="GameState ya tiene un análisis pendiente", headers={"Retry-After": "10"})
    app.state.accepting_analysis = True
    analysis_id = uuid4().hex
    directory = ROOT / analysis_id
    input_path = directory / "input.mp4"
    size = 0
    try:
        directory.mkdir(parents=True)
        with input_path.open("wb") as target:
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="El video supera el límite permitido")
                target.write(chunk)
        try:
            video_info = await asyncio.to_thread(inspect_video, input_path)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        metadata = {
            "analysis_id": analysis_id,
            "status": "queued",
            "created_at": utc_now(),
            "bytes": size,
            "video": video_info,
            "model": "SoccerNet GameState Reconstruction",
        }
        write_metadata(analysis_id, metadata)
        background_tasks.add_task(execute_analysis, analysis_id)
        return metadata
    except BaseException:
        app.state.accepting_analysis = False
        shutil.rmtree(directory, ignore_errors=True)
        raise


@app.get("/v1/analyses/{analysis_id}", dependencies=[Depends(require_api_key)])
def get_analysis(analysis_id: str) -> dict[str, Any]:
    return read_metadata(analysis_id)


@app.get("/v1/analyses/{analysis_id}/result", dependencies=[Depends(require_api_key)])
def get_result(analysis_id: str) -> Response:
    metadata = read_metadata(analysis_id)
    if metadata["status"] != "succeeded":
        raise HTTPException(status_code=409, detail=f"El análisis está {metadata['status']}")
    path = ROOT / analysis_id / "output" / "gamestate-observations.jsonl"
    return FileResponse(path, media_type="application/x-ndjson", filename=f"{analysis_id}.jsonl")


@app.get("/v1/analyses/{analysis_id}/log", dependencies=[Depends(require_api_key)])
def get_log(analysis_id: str) -> Response:
    read_metadata(analysis_id)
    path = ROOT / analysis_id / "analysis.log"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="El log todavía no existe")
    return FileResponse(path, media_type="text/plain", filename=f"{analysis_id}.log")

