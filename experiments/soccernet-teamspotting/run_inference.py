"""Ejecuta T-DEED de SoccerNet sobre el vídeo permitido de DV-US-17."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from hashlib import sha256
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
from types import SimpleNamespace
import time

import cv2
import numpy as np
import torch

from model.model import TDEEDModel
from util.dataset import load_classes


SOCCERNET_COMMIT = "091fed2fc35c33f7489f3596958a2fe385e37d65"
VIDEO_PATH = Path(os.environ.get("MENTOX_VIDEO_PATH", "/input/video.mp4"))
ANNOTATIONS_PATH = Path(
    os.environ.get("MENTOX_ANNOTATIONS_PATH", "/input/annotations.csv")
)
CHECKPOINT_PATH = Path("/models/checkpoint_best.pt")
OUTPUT_DIRECTORY = Path("/output")
RAW_OUTPUT = OUTPUT_DIRECTORY / "soccernet-predictions.json"
EVALUATION_INPUT = OUTPUT_DIRECTORY / "soccernet-evaluation-input.json"
CLIP_LENGTH = 100
CLIP_OVERLAP = 75
SOURCE_FPS = 25
STRIDE = 2
MODEL_FPS = SOURCE_FPS / STRIDE
TARGET_WIDTH = 796
TARGET_HEIGHT = 448
CONFIDENCE = 0.01
NMS_WINDOW_FRAMES = 12
REQUESTED_DEVICE = os.environ.get("MENTOX_VISION_DEVICE", "cpu").strip().lower()
CUDA_DEVICE = int(os.environ.get("MENTOX_CUDA_DEVICE", "0"))
CUDA_AMP = os.environ.get("MENTOX_CUDA_AMP", "1") == "1"
MEDIA_ID = os.environ.get("MENTOX_MEDIA_ID", "grf-dv-us-17").strip()
PERMISSION_BASIS = os.environ.get(
    "MENTOX_PERMISSION_BASIS", "project_generated"
).strip()
PERMISSION_REFERENCE = os.environ.get(
    "MENTOX_PERMISSION_REFERENCE",
    "docs/persona-1-datos-y-vision/evidencias/DV-US-17.md",
).strip()


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
                "label": row["class"].strip().lower(),
            }
            for row in csv.DictReader(stream)
        ]


def read_resampled_frames(path: Path) -> tuple[torch.Tensor, dict[str, object]]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError("OpenCV no pudo abrir el MP4")
    source_fps = capture.get(cv2.CAP_PROP_FPS)
    source_frames: list[np.ndarray] = []
    while True:
        available, frame = capture.read()
        if not available:
            break
        frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
        source_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    capture.release()
    if not source_frames or source_fps <= 0:
        raise RuntimeError("El MP4 no contiene cuadros o FPS válidos")

    duration_seconds = len(source_frames) / source_fps
    model_frame_count = max(1, math.ceil(duration_seconds * MODEL_FPS))
    sampled = []
    for model_index in range(model_frame_count):
        source_index = min(
            len(source_frames) - 1,
            round(model_index / MODEL_FPS * source_fps),
        )
        sampled.append(source_frames[source_index])
    tensor = torch.from_numpy(np.stack(sampled)).permute(0, 3, 1, 2)
    return tensor, {
        "source_fps": source_fps,
        "source_frames": len(source_frames),
        "model_fps": MODEL_FPS,
        "model_frames": model_frame_count,
        "duration_ms": round(duration_seconds * 1_000),
        "target_width": TARGET_WIDTH,
        "target_height": TARGET_HEIGHT,
    }


def model_arguments() -> SimpleNamespace:
    return SimpleNamespace(
        modality="rgb",
        temporal_arch="ed_sgp_mixer",
        radi_displacement=4,
        feature_arch="rny002_gsf",
        clip_len=CLIP_LENGTH,
        event_team=True,
        crop_dim=None,
        num_classes=12,
        n_layers=2,
        sgp_ks=9,
        sgp_r=4,
    )


def load_model(device: str) -> tuple[TDEEDModel, dict[int, str]]:
    args = model_arguments()
    model = TDEEDModel(device=device, args=args)
    classes = load_classes("data/soccernetball/class.txt", event_team=True)
    joint_classes = load_classes("data/soccernet/class.txt", event_team=True)
    model._model.update_pred_head([len(classes) // 2 + 1, len(joint_classes) // 2 + 1])
    model._num_classes = len(classes) // 2 + 1 + len(joint_classes) // 2 + 1
    state = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=True)
    model.load(state)
    return model, {value: key for key, value in classes.items()}


def aggregate_scores(
    model: TDEEDModel, frames: torch.Tensor, *, use_amp: bool
) -> np.ndarray:
    total = frames.shape[0]
    scores = np.zeros((total, 25), dtype=np.float32)
    support = np.zeros(total, dtype=np.int32)
    step = CLIP_LENGTH - CLIP_OVERLAP
    starts = list(range(0, max(1, total), step))
    if total > CLIP_LENGTH and starts[-1] + CLIP_LENGTH < total:
        starts.append(total - CLIP_LENGTH)

    for index, start in enumerate(starts, start=1):
        end = min(total, start + CLIP_LENGTH)
        clip = frames[start:end]
        valid = clip.shape[0]
        if valid < CLIP_LENGTH:
            padding = torch.zeros(
                (CLIP_LENGTH - valid, *clip.shape[1:]), dtype=clip.dtype
            )
            clip = torch.cat((clip, padding), dim=0)
        _, predicted = model.predict(clip, use_amp=use_amp)
        scores[start:end] += predicted[0, :valid, :25]
        support[start:end] += 1
        print(f"Clip {index}/{len(starts)} procesado", flush=True)
    scores /= np.maximum(support, 1)[:, None]
    return scores


def temporal_predictions(
    scores: np.ndarray, class_names: dict[int, str]
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for frame_index in range(scores.shape[0]):
        for class_index in range(1, 25):
            confidence = float(scores[frame_index, class_index])
            if confidence < CONFIDENCE:
                continue
            compound = class_names[class_index]
            label, team = compound.rsplit("-", 1)
            candidates.append(
                {
                    "frame": frame_index,
                    "timestamp_ms": round(frame_index / MODEL_FPS * 1_000),
                    "label": label.lower(),
                    "team": team,
                    "confidence": confidence,
                }
            )

    selected: list[dict[str, object]] = []
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for candidate in candidates:
        grouped.setdefault((str(candidate["label"]), str(candidate["team"])), []).append(
            candidate
        )
    for group in grouped.values():
        remaining = sorted(group, key=lambda item: float(item["confidence"]), reverse=True)
        while remaining:
            best = remaining.pop(0)
            selected.append(best)
            remaining = [
                item
                for item in remaining
                if abs(int(item["frame"]) - int(best["frame"])) > NMS_WINDOW_FRAMES
            ]
    selected.sort(key=lambda item: (int(item["timestamp_ms"]), str(item["label"])))
    for index, item in enumerate(selected):
        item["prediction_id"] = f"soccernet-{index:04d}"
        item["prediction_origin"] = "actual_model"
    return selected


def main() -> None:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    if not VIDEO_PATH.is_file() or not ANNOTATIONS_PATH.is_file():
        raise FileNotFoundError("Faltan el MP4 o las anotaciones temporales de DV-US-20")
    if REQUESTED_DEVICE not in {"cpu", "cuda"}:
        raise ValueError("MENTOX_VISION_DEVICE debe ser cpu o cuda")
    if REQUESTED_DEVICE == "cuda" and not torch.cuda.is_available():
        raise RuntimeError(
            "Se solicitó CUDA, pero PyTorch no detecta una GPU dentro del contenedor. "
            "Verifique NVIDIA Container Toolkit y el uso de --gpus all."
        )
    if REQUESTED_DEVICE == "cuda" and CUDA_DEVICE >= torch.cuda.device_count():
        raise RuntimeError(
            f"Se solicitó la GPU {CUDA_DEVICE}, pero solo hay "
            f"{torch.cuda.device_count()} GPU disponibles."
        )

    device = f"cuda:{CUDA_DEVICE}" if REQUESTED_DEVICE == "cuda" else "cpu"
    use_amp = REQUESTED_DEVICE == "cuda" and CUDA_AMP
    if REQUESTED_DEVICE == "cuda":
        torch.cuda.set_device(CUDA_DEVICE)

    frames, video = read_resampled_frames(VIDEO_PATH)
    model, class_names = load_model(device)
    started = time.perf_counter()
    scores = aggregate_scores(model, frames, use_amp=use_amp)
    if REQUESTED_DEVICE == "cuda":
        torch.cuda.synchronize(CUDA_DEVICE)
    processing_time_ms = (time.perf_counter() - started) * 1_000
    predictions = temporal_predictions(scores, class_names)
    versions = {
        package: importlib.metadata.version(package)
        for package in ("torch", "torchvision", "timm", "opencv-python-headless")
    }

    raw_document = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": "SoccerNet Team Ball Action Spotting",
        "source_repository": "https://github.com/SoccerNet/sn-teamspotting",
        "source_revision": SOCCERNET_COMMIT,
        "code_license": "GPL-3.0",
        "checkpoint_license_status": "not_declared_separately",
        "checkpoint_distribution": "not_redistributed",
        "checkpoint_sha256": file_sha256(CHECKPOINT_PATH),
        "media_sha256": file_sha256(VIDEO_PATH),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "device": device,
            "automatic_mixed_precision": use_amp,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda,
            "gpu_name": (
                torch.cuda.get_device_name(CUDA_DEVICE)
                if REQUESTED_DEVICE == "cuda"
                else None
            ),
            "gpu_count": torch.cuda.device_count(),
            "gpu_memory_bytes": (
                torch.cuda.get_device_properties(CUDA_DEVICE).total_memory
                if REQUESTED_DEVICE == "cuda"
                else None
            ),
            "versions": versions,
        },
        "parameters": {
            "classes": 12,
            "confidence": CONFIDENCE,
            "clip_length": CLIP_LENGTH,
            "clip_overlap": CLIP_OVERLAP,
            "source_fps": SOURCE_FPS,
            "stride": STRIDE,
            "model_fps": MODEL_FPS,
            "resolution": [TARGET_WIDTH, TARGET_HEIGHT],
            "nms_window_frames": NMS_WINDOW_FRAMES,
        },
        "video": video,
        "processing_time_ms": processing_time_ms,
        "predictions": predictions,
    }
    RAW_OUTPUT.write_text(
        json.dumps(raw_document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    classes = [
        line.strip().lower()
        for line in Path("data/soccernetball/class.txt").read_text().splitlines()
        if line.strip()
    ]
    evaluation_document = {
        "media": {
            "media_id": MEDIA_ID,
            "sha256": raw_document["media_sha256"],
            "duration_ms": video["duration_ms"],
            "permission_basis": PERMISSION_BASIS,
            "permission_reference": PERMISSION_REFERENCE,
        },
        "model": {
            "provider": "SoccerNet Team Ball Action Spotting",
            "model_name": "T-DEED baseline 2025",
            "model_version": raw_document["checkpoint_sha256"],
            "source_revision": SOCCERNET_COMMIT,
            "task": "action_spotting",
            "classes": classes,
            "parameters": {
                "confidence": str(CONFIDENCE),
                "device": device,
                "automatic_mixed_precision": str(use_amp),
                "model_fps": str(MODEL_FPS),
                "checkpoint_license_status": "not_declared_separately",
            },
            "prediction_origin": "actual_model",
        },
        "references": load_references(),
        "predictions": [
            {
                "prediction_id": item["prediction_id"],
                "timestamp_ms": item["timestamp_ms"],
                "label": item["label"],
                "confidence": item["confidence"],
            }
            for item in predictions
        ],
        "processing_time_ms": processing_time_ms,
        "temporal_tolerance_ms": 1_000,
        "integration_thresholds": {
            "minimum_precision": 0.5,
            "minimum_recall": 0.5,
            "maximum_realtime_factor": 3.0,
        },
    }
    EVALUATION_INPUT.write_text(
        json.dumps(evaluation_document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "frames_processed": video["model_frames"],
                "prediction_count": len(predictions),
                "processing_time_ms": round(processing_time_ms, 3),
                "raw_output": str(RAW_OUTPUT),
                "evaluation_input": str(EVALUATION_INPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
