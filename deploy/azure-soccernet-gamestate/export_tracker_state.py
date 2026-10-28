"""Exporta un TrackerState de TrackLab a JSONL auditable."""

from __future__ import annotations

import argparse
import json
import math
import zipfile
from pathlib import Path

import pandas as pd


def plain(value):
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if hasattr(value, "item"):
        return plain(value.item())
    return value


def export_state(state_path: Path, output_path: Path) -> int:
    rows_written = 0
    with zipfile.ZipFile(state_path) as archive, output_path.open("w", encoding="utf-8") as output:
        detection_files = sorted(
            name for name in archive.namelist()
            if name.endswith(".pkl") and not name.endswith("_image.pkl")
        )
        for detection_name in detection_files:
            video_id = detection_name[:-4]
            with archive.open(detection_name, force_zip64=True) as source:
                detections = pd.read_pickle(source)
            image_name = f"{video_id}_image.pkl"
            images = None
            if image_name in archive.namelist():
                with archive.open(image_name, force_zip64=True) as source:
                    images = pd.read_pickle(source)
            for detection_id, detection in detections.iterrows():
                image_id = detection.get("image_id")
                frame_index = image_id
                if images is not None and image_id in images.index and "frame" in images.columns:
                    frame_index = images.loc[image_id].get("frame", image_id)
                row = {
                    "schema_version": "1",
                    "source": "soccernet-gamestate",
                    "video_id": str(detection.get("video_id", video_id)),
                    "detection_id": str(detection_id),
                    "image_id": plain(image_id),
                    "frame_index": int(frame_index),
                    "track_id": plain(detection.get("track_id")),
                    "role": plain(detection.get("role")),
                    "team": plain(detection.get("team")),
                    "team_cluster": plain(detection.get("team_cluster")),
                    "jersey_number": plain(detection.get("jersey_number")),
                    "bbox_ltwh": plain(detection.get("bbox_ltwh")),
                    "bbox_pitch": plain(detection.get("bbox_pitch")),
                    "bbox_confidence": plain(detection.get("track_bbox_conf", detection.get("bbox_conf"))),
                    "role_confidence": plain(detection.get("role_confidence")),
                    "jersey_confidence": plain(detection.get("jn_confidence")),
                }
                output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                rows_written += 1
    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = export_state(args.state, args.output)
    print(json.dumps({"status": "complete", "observations": count, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

