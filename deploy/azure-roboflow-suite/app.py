"""API GPU conjunta para los tres modelos de fútbol usados de Roboflow Sports."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from hmac import compare_digest
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import cv2
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
import numpy as np
import torch
from ultralytics import YOLO

MODEL_PATHS = {
    "player": Path("/models/football-player-detection.pt"),
    "ball": Path("/models/football-ball-detection.pt"),
    "pitch": Path("/models/football-pitch-detection.pt"),
}
MAX_IMAGE_BYTES = int(os.getenv("MENTOX_MAX_IMAGE_BYTES", str(15 * 1024 * 1024)))
CONFIDENCE = float(os.getenv("MENTOX_VISION_CONFIDENCE", "0.25"))
IMAGE_SIZE = int(os.getenv("MENTOX_VISION_IMAGE_SIZE", "960"))
API_KEY = os.getenv("MENTOX_MODEL_API_KEY", "")


def require_api_key(supplied: Annotated[str | None, Header(alias="X-API-Key")] = None) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="MENTOX_MODEL_API_KEY no está configurada")
    if supplied is None or not compare_digest(supplied, API_KEY):
        raise HTTPException(status_code=401, detail="Credencial de inferencia inválida")


def decode_image(content: bytes) -> np.ndarray:
    if not content:
        raise HTTPException(status_code=422, detail="La imagen está vacía")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite permitido")
    frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="El archivo no es una imagen válida")
    return frame


def serialize_result(model_name: str, result: Any, width: int, height: int) -> dict[str, Any]:
    names = {int(key): value for key, value in result.names.items()}
    detections: list[dict[str, Any]] = []
    boxes = result.boxes
    if boxes is not None:
        keypoints_xy = result.keypoints.xy.cpu().tolist() if result.keypoints is not None else []
        keypoints_conf = (
            result.keypoints.conf.cpu().tolist()
            if result.keypoints is not None and result.keypoints.conf is not None
            else []
        )
        for index, (xyxy, confidence, class_id) in enumerate(zip(
            boxes.xyxy.cpu().tolist(), boxes.conf.cpu().tolist(), boxes.cls.int().cpu().tolist(), strict=True
        )):
            x1, y1, x2, y2 = xyxy
            item: dict[str, Any] = {
                "class_id": class_id,
                "label": names[class_id],
                "confidence": confidence,
                "bounding_box": [x1 / width, y1 / height, x2 / width, y2 / height],
                "track_id": None,
                "player_id": None,
            }
            if index < len(keypoints_xy):
                item["keypoints"] = [
                    {
                        "x": point[0] / width,
                        "y": point[1] / height,
                        "confidence": keypoints_conf[index][point_index] if index < len(keypoints_conf) else None,
                    }
                    for point_index, point in enumerate(keypoints_xy[index])
                ]
            detections.append(item)
    return {"model": model_name, "detections": detections}


def predict(models: dict[str, YOLO], selected: list[str], image: np.ndarray) -> dict[str, Any]:
    height, width = image.shape[:2]
    started = perf_counter()
    outputs = []
    for model_name in selected:
        result = models[model_name].predict(
            image, device=0, half=True, imgsz=IMAGE_SIZE, conf=CONFIDENCE, verbose=False
        )[0]
        outputs.append(serialize_result(model_name, result, width, height))
    return {
        "device": torch.cuda.get_device_name(0),
        "image": {"width": width, "height": height},
        "inference_ms": round((perf_counter() - started) * 1000, 3),
        "results": outputs,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_KEY:
        raise RuntimeError("MENTOX_MODEL_API_KEY es obligatoria")
    missing = [str(path) for path in MODEL_PATHS.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Faltan pesos: {', '.join(missing)}")
    if not torch.cuda.is_available():
        raise RuntimeError("Azure no expuso una GPU CUDA al contenedor")
    models = {name: YOLO(str(path)) for name, path in MODEL_PATHS.items()}
    warmup = np.zeros((640, 640, 3), dtype=np.uint8)
    for model in models.values():
        await asyncio.to_thread(
            model.predict, warmup, device=0, half=True, imgsz=IMAGE_SIZE, conf=CONFIDENCE, verbose=False
        )
    app.state.models = models
    app.state.inference_lock = asyncio.Lock()
    yield


app = FastAPI(title="Mentox Roboflow Football Suite", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> dict[str, Any]:
    if not hasattr(app.state, "models") or not torch.cuda.is_available():
        raise HTTPException(status_code=503, detail="Los modelos todavía no están listos")
    return {"status": "ready", "models": list(MODEL_PATHS), "device": torch.cuda.get_device_name(0)}


@app.post("/v1/predict", dependencies=[Depends(require_api_key)])
async def predict_image(
    image: Annotated[UploadFile, File()],
    models: Annotated[str, Query(description="player,ball,pitch o all")] = "all",
) -> dict[str, Any]:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use JPEG, PNG o WebP")
    selected = list(MODEL_PATHS) if models == "all" else [item.strip() for item in models.split(",") if item.strip()]
    invalid = sorted(set(selected) - MODEL_PATHS.keys())
    if not selected or invalid:
        raise HTTPException(status_code=422, detail=f"Modelos inválidos: {invalid or selected}")
    frame = decode_image(await image.read())
    async with app.state.inference_lock:
        return await asyncio.to_thread(predict, app.state.models, selected, frame)

