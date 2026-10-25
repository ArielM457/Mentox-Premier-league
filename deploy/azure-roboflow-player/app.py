"""API mínima de inferencia para el detector espacial de Roboflow Sports."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from hmac import compare_digest
import os
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import cv2
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
import numpy as np
import torch
from ultralytics import YOLO

MODEL_PATH = Path(os.getenv("MENTOX_MODEL_PATH", "/models/football-player-detection.pt"))
MODEL_NAME = "roboflow-football-player-detection"
MAX_IMAGE_BYTES = int(os.getenv("MENTOX_MAX_IMAGE_BYTES", str(15 * 1024 * 1024)))
CONFIDENCE = float(os.getenv("MENTOX_VISION_CONFIDENCE", "0.25"))
IMAGE_SIZE = int(os.getenv("MENTOX_PLAYER_IMAGE_SIZE", "960"))
API_KEY = os.getenv("MENTOX_MODEL_API_KEY", "")


def require_api_key(
    supplied_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if not API_KEY:
        raise HTTPException(status_code=503, detail="MENTOX_MODEL_API_KEY no está configurada")
    if supplied_key is None or not compare_digest(supplied_key, API_KEY):
        raise HTTPException(status_code=401, detail="Credencial de inferencia inválida")


def decode_image(content: bytes) -> np.ndarray:
    if not content:
        raise HTTPException(status_code=422, detail="La imagen está vacía")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen supera el límite permitido")
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=422, detail="El archivo no es una imagen válida")
    return image


def predict(model: YOLO, image: np.ndarray) -> dict[str, Any]:
    height, width = image.shape[:2]
    started = perf_counter()
    result = model.predict(
        image,
        device=0,
        half=True,
        imgsz=IMAGE_SIZE,
        conf=CONFIDENCE,
        verbose=False,
    )[0]
    boxes = result.boxes
    detections: list[dict[str, Any]] = []
    if boxes is not None:
        names = {int(key): value for key, value in result.names.items()}
        for xyxy, confidence, class_id in zip(
            boxes.xyxy.cpu().tolist(),
            boxes.conf.cpu().tolist(),
            boxes.cls.int().cpu().tolist(),
            strict=True,
        ):
            x1, y1, x2, y2 = xyxy
            detections.append(
                {
                    "class_id": class_id,
                    "label": names[class_id],
                    "confidence": confidence,
                    "bounding_box": [x1 / width, y1 / height, x2 / width, y2 / height],
                    "track_id": None,
                    "player_id": None,
                }
            )
    return {
        "model": MODEL_NAME,
        "device": torch.cuda.get_device_name(0),
        "image": {"width": width, "height": height},
        "inference_ms": round((perf_counter() - started) * 1000, 3),
        "detections": detections,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not API_KEY:
        raise RuntimeError("MENTOX_MODEL_API_KEY es obligatoria")
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"No se encontró el peso {MODEL_PATH}")
    if not torch.cuda.is_available():
        raise RuntimeError("Azure no expuso una GPU CUDA al contenedor")

    model = YOLO(str(MODEL_PATH))
    warmup = np.zeros((640, 640, 3), dtype=np.uint8)
    await asyncio.to_thread(
        model.predict,
        warmup,
        device=0,
        half=True,
        imgsz=IMAGE_SIZE,
        conf=CONFIDENCE,
        verbose=False,
    )
    app.state.model = model
    app.state.inference_lock = asyncio.Lock()
    yield


app = FastAPI(
    title="Mentox Roboflow Player Detector",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready() -> dict[str, object]:
    ready = hasattr(app.state, "model") and torch.cuda.is_available()
    if not ready:
        raise HTTPException(status_code=503, detail="El modelo todavía no está listo")
    return {
        "status": "ready",
        "model": MODEL_NAME,
        "device": torch.cuda.get_device_name(0),
        "image_size": IMAGE_SIZE,
        "confidence": CONFIDENCE,
    }


@app.post("/v1/predict", dependencies=[Depends(require_api_key)])
async def predict_image(image: Annotated[UploadFile, File()]) -> dict[str, Any]:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Use JPEG, PNG o WebP")
    frame = decode_image(await image.read())
    async with app.state.inference_lock:
        return await asyncio.to_thread(predict, app.state.model, frame)

