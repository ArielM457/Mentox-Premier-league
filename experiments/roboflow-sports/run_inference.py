"""Ejecuta los tres modelos oficiales de fútbol de Roboflow Sports."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
import urllib.error
import urllib.request

import cv2
import torch
from ultralytics import YOLO

SPORTS_COMMIT = "42c80c06b6b65a7f89455b89fe31cdf4c38ba227"
VIDEO_PATH = Path(os.getenv("MENTOX_VIDEO_PATH", "/input/video.mp4"))
ANNOTATIONS_PATH = Path(os.getenv("MENTOX_ANNOTATIONS_PATH", "/input/annotations.csv"))
OUTPUT_DIRECTORY = Path("/output")
RAW_OUTPUT = OUTPUT_DIRECTORY / "roboflow-sports-predictions.json"
EVALUATION_INPUT = OUTPUT_DIRECTORY / "roboflow-sports-evaluation-input.json"
ANNOTATED_VIDEO = OUTPUT_DIRECTORY / "roboflow-sports-annotated.mp4"
MODEL_PATHS = {
    "player": Path("/models/football-player-detection.pt"),
    "ball": Path("/models/football-ball-detection.pt"),
    "pitch": Path("/models/football-pitch-detection.pt"),
}
CONFIDENCE = float(os.getenv("MENTOX_VISION_CONFIDENCE", "0.10"))
IMAGE_SIZES = {
    role: int(os.getenv(f"MENTOX_{role.upper()}_IMAGE_SIZE", "1280"))
    for role in MODEL_PATHS
}
PITCH_STRIDE = max(1, int(os.getenv("MENTOX_PITCH_STRIDE", "5")))
REQUESTED_DEVICE = os.getenv("MENTOX_VISION_DEVICE", "cpu").strip().lower()
CUDA_DEVICE = os.getenv("MENTOX_CUDA_DEVICE", "0").strip()
CUDA_HALF = os.getenv("MENTOX_CUDA_HALF", "1") == "1"
REQUESTED_MODELS = os.getenv("MENTOX_VISION_MODELS", "all").strip().lower()
MEDIA_ID = os.getenv("MENTOX_MEDIA_ID", "grf-dv-us-17").strip()
PERMISSION_BASIS = os.getenv("MENTOX_PERMISSION_BASIS", "project_generated").strip()
PERMISSION_REFERENCE = os.getenv(
    "MENTOX_PERMISSION_REFERENCE",
    "docs/persona-1-datos-y-vision/evidencias/DV-US-17.md",
).strip()
TRACKER = "bytetrack.yaml"
ANNOTATED_FRAMES = {50, 150, 250}
LIVE_ENDPOINT = os.getenv("MENTOX_LIVE_ENDPOINT", "").strip()


def selected_roles() -> tuple[str, ...]:
    if REQUESTED_MODELS == "all":
        return tuple(MODEL_PATHS)
    roles = tuple(item.strip() for item in REQUESTED_MODELS.split(",") if item.strip())
    unknown = sorted(set(roles) - set(MODEL_PATHS))
    if not roles or unknown:
        raise ValueError(
            "MENTOX_VISION_MODELS debe ser all o una lista de player,ball,pitch; "
            f"valores desconocidos: {unknown}"
        )
    return roles


def publish_live(item: dict[str, object]) -> None:
    if not LIVE_ENDPOINT:
        return
    payload = {
        "observation_id": item["prediction_id"],
        "source": f"roboflow-{item['model_role']}",
        "kind": "spatial_detection",
        "timestamp_ms": item["timestamp_ms"],
        "payload": item,
    }
    request = urllib.request.Request(
        LIVE_ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status != 202:
                raise RuntimeError(f"El backend respondió {response.status}")
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Aviso: observación en vivo no publicada: {error}", flush=True)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_references() -> list[dict[str, object]]:
    with ANNOTATIONS_PATH.open(encoding="utf-8", newline="") as stream:
        return [
            {
                "observation_id": row["annotation_id"],
                "timestamp_ms": int(row["video_time_ms"]),
                "label": row["class"],
                "bounding_box": [
                    float(row["x_min_norm"]), float(row["y_min_norm"]),
                    float(row["x_max_norm"]), float(row["y_max_norm"]),
                ],
            }
            for row in csv.DictReader(stream)
        ]


def box_items(result, *, role, frame_index, timestamp_ms, width, height, started):
    boxes = result.boxes
    if boxes is None:
        return []
    xyxy = boxes.xyxy.cpu().tolist()
    confidences = boxes.conf.cpu().tolist()
    classes = boxes.cls.int().cpu().tolist()
    track_ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(xyxy)
    names = {int(key): value for key, value in result.names.items()}
    items = []
    for index, (box, confidence, class_id, track_id) in enumerate(
        zip(xyxy, confidences, classes, track_ids, strict=True)
    ):
        x1, y1, x2, y2 = box
        items.append({
            "prediction_id": f"{role}-frame-{frame_index:06d}-det-{index:03d}",
            "frame": frame_index,
            "timestamp_ms": timestamp_ms,
            "label": names[class_id],
            "class_id": class_id,
            "confidence": confidence,
            "bounding_box": [x1 / width, y1 / height, x2 / width, y2 / height],
            "track_id": track_id,
            "player_id": None,
            "model_role": role,
            "prediction_origin": "actual_model",
            "processing_delay_ms": max(0, round((time.perf_counter() - started) * 1000) - timestamp_ms),
        })
    return items


def pitch_items(result, *, frame_index, timestamp_ms, width, height, started):
    if result.keypoints is None or result.keypoints.xy is None:
        return []
    groups = result.keypoints.xy.cpu().tolist()
    confidence_groups = (
        result.keypoints.conf.cpu().tolist()
        if result.keypoints.conf is not None
        else [[None] * len(points) for points in groups]
    )
    items = []
    for index, (points, confidences) in enumerate(zip(groups, confidence_groups, strict=True)):
        normalized = [
            {"x": point[0] / width, "y": point[1] / height,
             "confidence": None if confidence is None else float(confidence)}
            for point, confidence in zip(points, confidences, strict=True)
        ]
        available = [point["confidence"] for point in normalized if point["confidence"] is not None]
        items.append({
            "prediction_id": f"pitch-frame-{frame_index:06d}-pose-{index:02d}",
            "frame": frame_index,
            "timestamp_ms": timestamp_ms,
            "label": "pitch_keypoints",
            "confidence": sum(available) / len(available) if available else 0.0,
            "keypoints": normalized,
            "track_id": None,
            "player_id": None,
            "model_role": "pitch",
            "prediction_origin": "actual_model",
            "processing_delay_ms": max(0, round((time.perf_counter() - started) * 1000) - timestamp_ms),
        })
    return items


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not VIDEO_PATH.is_file() or not ANNOTATIONS_PATH.is_file():
        raise FileNotFoundError("Faltan el MP4 o las anotaciones")
    roles = selected_roles()
    missing = [str(MODEL_PATHS[role]) for role in roles if not MODEL_PATHS[role].is_file()]
    if missing:
        raise FileNotFoundError(f"Faltan pesos: {missing}")
    if REQUESTED_DEVICE not in {"cpu", "cuda"}:
        raise ValueError("MENTOX_VISION_DEVICE debe ser cpu o cuda")
    if REQUESTED_DEVICE == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "Se solicitó CUDA, pero PyTorch no detecta la GPU dentro del contenedor. "
            "Verifique el controlador y NVIDIA Container Toolkit."
        )
    device = f"cuda:{CUDA_DEVICE}" if REQUESTED_DEVICE == "cuda" else "cpu"
    use_half = REQUESTED_DEVICE == "cuda" and CUDA_HALF
    precision_arguments = {"quantize": 16} if use_half else {}
    models = {role: YOLO(str(MODEL_PATHS[role])) for role in roles}

    capture = cv2.VideoCapture(str(VIDEO_PATH))
    if not capture.isOpened():
        raise RuntimeError("OpenCV no pudo abrir el MP4")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = round(total_frames / fps * 1000)
    writer = cv2.VideoWriter(str(ANNOTATED_VIDEO), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV no pudo crear el vídeo anotado")

    predictions, pitch_observations = [], []
    counts = {role: 0 for role in roles}
    frame_index = 0
    started = time.perf_counter()
    try:
        while capture.isOpened():
            available, frame = capture.read()
            if not available:
                break
            annotated = frame.copy()
            timestamp_ms = round(frame_index / fps * 1000)
            if "player" in models:
                result = models["player"].track(
                    frame, persist=True, tracker=TRACKER, device=device,
                    imgsz=IMAGE_SIZES["player"], conf=CONFIDENCE,
                    verbose=False, **precision_arguments,
                )[0]
                items = box_items(result, role="player", frame_index=frame_index,
                                  timestamp_ms=timestamp_ms, width=width, height=height, started=started)
                predictions.extend(items)
                counts["player"] += len(items)
                annotated = result.plot(img=annotated)
                for item in items:
                    publish_live(item)
            if "ball" in models:
                result = models["ball"].predict(
                    frame, device=device, imgsz=IMAGE_SIZES["ball"],
                    conf=CONFIDENCE, verbose=False, **precision_arguments,
                )[0]
                items = box_items(result, role="ball", frame_index=frame_index,
                                  timestamp_ms=timestamp_ms, width=width, height=height, started=started)
                predictions.extend(items)
                counts["ball"] += len(items)
                for item in items:
                    x1, y1, x2, y2 = item["bounding_box"]
                    cv2.rectangle(annotated, (round(x1 * width), round(y1 * height)),
                                  (round(x2 * width), round(y2 * height)), (0, 255, 255), 3)
                    publish_live(item)
            if "pitch" in models and frame_index % PITCH_STRIDE == 0:
                result = models["pitch"].predict(
                    frame, device=device, imgsz=IMAGE_SIZES["pitch"],
                    conf=CONFIDENCE, verbose=False, **precision_arguments,
                )[0]
                items = pitch_items(result, frame_index=frame_index, timestamp_ms=timestamp_ms,
                                    width=width, height=height, started=started)
                pitch_observations.extend(items)
                counts["pitch"] += len(items)
                for item in items:
                    for point in item["keypoints"]:
                        if point["confidence"] is None or point["confidence"] >= CONFIDENCE:
                            cv2.circle(annotated, (round(point["x"] * width), round(point["y"] * height)),
                                       4, (255, 0, 255), -1)
                    publish_live(item)
            writer.write(annotated)
            frame_index += 1
            if frame_index % max(1, round(fps * 5)) == 0:
                print(f"Procesados {frame_index}/{total_frames} cuadros", flush=True)
    finally:
        capture.release()
        writer.release()
    processing_time_ms = (time.perf_counter() - started) * 1000

    versions = {name: importlib.metadata.version(name) for name in
                ("sports", "ultralytics", "supervision", "torch", "torchvision")}
    model_metadata = {
        role: {
            "file": MODEL_PATHS[role].name,
            "sha256": file_sha256(MODEL_PATHS[role]),
            "task": models[role].task,
            "classes": list(models[role].names.values()) if models[role].names else [],
            "image_size": IMAGE_SIZES[role],
        }
        for role in roles
    }
    raw_document = {
        "schema_version": "2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": "Roboflow Sports",
        "source_repository": "https://github.com/roboflow/sports",
        "source_revision": SPORTS_COMMIT,
        "sports_license": "MIT",
        "ultralytics_license": "AGPL-3.0-or-later",
        "weights_license_status": "not_declared_in_official_repository",
        "weights_distribution": "not_redistributed",
        "models": model_metadata,
        "media_sha256": file_sha256(VIDEO_PATH),
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "device": device, "half_precision": use_half,
            "cuda_available": torch.cuda.is_available(), "cuda_version": torch.version.cuda,
            "gpu_name": torch.cuda.get_device_name(int(CUDA_DEVICE)) if REQUESTED_DEVICE == "cuda" else None,
            "gpu_count": torch.cuda.device_count(), "versions": versions,
        },
        "parameters": {"confidence": CONFIDENCE, "image_sizes": IMAGE_SIZES,
                       "pitch_stride": PITCH_STRIDE, "tracker": TRACKER},
        "video": {"width": width, "height": height, "fps": fps,
                  "frames_declared": total_frames, "frames_processed": frame_index,
                  "duration_ms": duration_ms},
        "processing_time_ms": processing_time_ms,
        "prediction_counts": counts,
        "predictions": predictions,
        "pitch_observations": pitch_observations,
    }
    RAW_OUTPUT.write_text(json.dumps(raw_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ball_predictions = [
        {"prediction_id": item["prediction_id"], "timestamp_ms": item["timestamp_ms"],
         "label": "ball", "confidence": item["confidence"], "bounding_box": item["bounding_box"]}
        for item in predictions
        if item["model_role"] == "ball" and item["frame"] in ANNOTATED_FRAMES
    ]
    evaluation_document = {
        "media": {"media_id": MEDIA_ID, "sha256": raw_document["media_sha256"],
                  "duration_ms": duration_ms, "permission_basis": PERMISSION_BASIS,
                  "permission_reference": PERMISSION_REFERENCE},
        "model": {"provider": "Roboflow Sports", "model_name": "football-ball-detection.pt",
                  "model_version": model_metadata.get("ball", {}).get("sha256", "not_executed"),
                  "source_revision": SPORTS_COMMIT, "task": "spatial_detection", "classes": ["ball"],
                  "parameters": {"confidence": str(CONFIDENCE), "device": device,
                                 "image_size": str(IMAGE_SIZES["ball"]),
                                 "weights_license_status": "not_declared"},
                  "prediction_origin": "actual_model"},
        "references": load_references(), "predictions": ball_predictions,
        "processing_time_ms": processing_time_ms, "temporal_tolerance_ms": 100,
        "iou_threshold": 0.5,
        "integration_thresholds": {"minimum_precision": 0.5, "minimum_recall": 0.5,
                                   "maximum_realtime_factor": 3.0},
    }
    EVALUATION_INPUT.write_text(json.dumps(evaluation_document, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
    print(json.dumps({"frames_processed": frame_index, "models_executed": list(roles),
                      "prediction_counts": counts, "processing_time_ms": round(processing_time_ms, 3),
                      "device": device, "half_precision": use_half, "raw_output": str(RAW_OUTPUT),
                      "evaluation_input": str(EVALUATION_INPUT), "annotated_video": str(ANNOTATED_VIDEO)},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
