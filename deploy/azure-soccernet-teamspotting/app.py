"""API de spotting temporal T-DEED para clips autorizados de fútbol."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from hmac import compare_digest
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
from types import SimpleNamespace
from typing import Annotated, Any

import cv2
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
import numpy as np
import torch

from model.model import TDEEDModel
from util.dataset import load_classes

CHECKPOINT_PATH = Path("/models/checkpoint_best.pt")
CLIP_LENGTH = 100
CLIP_OVERLAP = 75
MODEL_FPS = 12.5
TARGET_WIDTH = 796
TARGET_HEIGHT = 448
NMS_WINDOW_FRAMES = 12
CONFIDENCE = float(os.getenv("MENTOX_TEAMSPOTTING_CONFIDENCE", "0.01"))
MAX_VIDEO_BYTES = int(os.getenv("MENTOX_MAX_VIDEO_BYTES", str(120 * 1024 * 1024)))
MAX_DURATION_SECONDS = float(os.getenv("MENTOX_MAX_VIDEO_SECONDS", "240"))
API_KEY = os.getenv("MENTOX_MODEL_API_KEY", "")


def require_api_key(supplied: Annotated[str | None, Header(alias="X-API-Key")] = None) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="MENTOX_MODEL_API_KEY no está configurada")
    if supplied is None or not compare_digest(supplied, API_KEY):
        raise HTTPException(status_code=401, detail="Credencial de inferencia inválida")


def model_arguments() -> SimpleNamespace:
    return SimpleNamespace(
        modality="rgb", temporal_arch="ed_sgp_mixer", radi_displacement=4,
        feature_arch="rny002_gsf", clip_len=CLIP_LENGTH, event_team=True,
        crop_dim=None, num_classes=12, n_layers=2, sgp_ks=9, sgp_r=4,
    )


def load_model() -> tuple[TDEEDModel, dict[int, str]]:
    device = "cuda:0"
    model = TDEEDModel(device=device, args=model_arguments())
    classes = load_classes("data/soccernetball/class.txt", event_team=True)
    joint = load_classes("data/soccernet/class.txt", event_team=True)
    model._model.update_pred_head([len(classes) // 2 + 1, len(joint) // 2 + 1])
    model._num_classes = len(classes) // 2 + 1 + len(joint) // 2 + 1
    state = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    model.load(state)
    return model, {value: key for key, value in classes.items()}


def read_frames(path: Path) -> tuple[torch.Tensor, dict[str, Any]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("OpenCV no pudo abrir el MP4")
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    source_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if source_fps <= 0 or source_count <= 0:
        capture.release()
        raise ValueError("El MP4 no informa FPS o cuadros válidos")
    duration = source_count / source_fps
    if duration > MAX_DURATION_SECONDS:
        capture.release()
        raise ValueError(f"El clip dura {duration:.2f}s; el máximo es {MAX_DURATION_SECONDS:.0f}s")
    target_count = max(1, math.ceil(duration * MODEL_FPS))
    sampled: list[np.ndarray] = []
    for model_index in range(target_count):
        source_index = min(source_count - 1, round(model_index / MODEL_FPS * source_fps))
        capture.set(cv2.CAP_PROP_POS_FRAMES, source_index)
        available, frame = capture.read()
        if not available:
            capture.release()
            raise ValueError(f"No se pudo leer el cuadro {source_index}")
        frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
        sampled.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    capture.release()
    tensor = torch.from_numpy(np.stack(sampled)).permute(0, 3, 1, 2)
    return tensor, {
        "source_fps": source_fps, "source_frames": source_count,
        "model_fps": MODEL_FPS, "model_frames": target_count,
        "duration_ms": round(duration * 1000),
        "target_width": TARGET_WIDTH, "target_height": TARGET_HEIGHT,
    }


def aggregate_scores(model: TDEEDModel, frames: torch.Tensor) -> np.ndarray:
    total = frames.shape[0]
    scores = np.zeros((total, 25), dtype=np.float32)
    support = np.zeros(total, dtype=np.int32)
    step = CLIP_LENGTH - CLIP_OVERLAP
    starts = list(range(0, max(1, total), step))
    if total > CLIP_LENGTH and starts[-1] + CLIP_LENGTH < total:
        starts.append(total - CLIP_LENGTH)
    for start in starts:
        end = min(total, start + CLIP_LENGTH)
        clip = frames[start:end]
        valid = clip.shape[0]
        if valid < CLIP_LENGTH:
            clip = torch.cat((clip, torch.zeros((CLIP_LENGTH - valid, *clip.shape[1:]), dtype=clip.dtype)))
        _, predicted = model.predict(clip, use_amp=True)
        scores[start:end] += predicted[0, :valid, :25]
        support[start:end] += 1
    return scores / np.maximum(support, 1)[:, None]


def temporal_predictions(scores: np.ndarray, names: dict[int, str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for frame in range(scores.shape[0]):
        for class_index in range(1, 25):
            confidence = float(scores[frame, class_index])
            if confidence < CONFIDENCE:
                continue
            label, team = names[class_index].rsplit("-", 1)
            grouped.setdefault((label, team), []).append({
                "frame": frame, "video_time_ms": round(frame / MODEL_FPS * 1000),
                "label": label.lower(), "team": team, "confidence": confidence,
            })
    selected: list[dict[str, Any]] = []
    for group in grouped.values():
        remaining = sorted(group, key=lambda item: item["confidence"], reverse=True)
        while remaining:
            best = remaining.pop(0)
            selected.append(best)
            remaining = [item for item in remaining if abs(item["frame"] - best["frame"]) > NMS_WINDOW_FRAMES]
    selected.sort(key=lambda item: (item["video_time_ms"], item["label"]))
    for index, item in enumerate(selected):
        item["prediction_id"] = f"soccernet-{index:04d}"
        item["prediction_origin"] = "actual_model"
    return selected


def run_prediction(model: TDEEDModel, names: dict[int, str], path: Path) -> dict[str, Any]:
    frames, video = read_frames(path)
    started = perf_counter()
    scores = aggregate_scores(model, frames)
    torch.cuda.synchronize(0)
    return {
        "model": "SoccerNet T-DEED TeamSpotting",
        "device": torch.cuda.get_device_name(0),
        "video": video,
        "processing_time_ms": round((perf_counter() - started) * 1000, 3),
        "predictions": temporal_predictions(scores, names),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_KEY:
        raise RuntimeError("MENTOX_MODEL_API_KEY es obligatoria")
    if not CHECKPOINT_PATH.is_file():
        raise RuntimeError(f"No se encontró {CHECKPOINT_PATH}")
    if not torch.cuda.is_available():
        raise RuntimeError("Azure no expuso una GPU CUDA al contenedor")
    torch.cuda.set_device(0)
    app.state.model, app.state.class_names = await asyncio.to_thread(load_model)
    app.state.inference_lock = asyncio.Lock()
    yield


app = FastAPI(title="Mentox SoccerNet TeamSpotting", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> dict[str, Any]:
    if not hasattr(app.state, "model") or not torch.cuda.is_available():
        raise HTTPException(status_code=503, detail="El modelo todavía no está listo")
    return {"status": "ready", "model": "SoccerNet T-DEED TeamSpotting", "device": torch.cuda.get_device_name(0)}


@app.post("/v1/predict", dependencies=[Depends(require_api_key)])
async def predict_video(video: Annotated[UploadFile, File()]) -> dict[str, Any]:
    if video.content_type not in {"video/mp4", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Use un vídeo MP4")
    size = 0
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=".mp4", delete=False, dir="/tmp") as target:
            temporary_path = Path(target.name)
            while chunk := await video.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(status_code=413, detail="El vídeo supera el límite permitido")
                target.write(chunk)
        async with app.state.inference_lock:
            try:
                return await asyncio.to_thread(run_prediction, app.state.model, app.state.class_names, temporary_path)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

