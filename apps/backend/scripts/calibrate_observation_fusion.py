"""Calibra candidatos de fusión sobre exportaciones reales de DV-US-19/20."""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from match_intelligence.application.candidate_fusion import (
    CandidateFusionPolicy,
    CandidateFusionService,
    ImageBox,
    SpatialDetection,
    TemporalAction,
    suppress_competing_candidates,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_spatial(path: Path) -> tuple[dict[str, Any], tuple[SpatialDetection, ...]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    detections = tuple(
        SpatialDetection(
            prediction_id=item["prediction_id"],
            timestamp_ms=item["timestamp_ms"],
            label=item["label"],
            confidence=item["confidence"],
            bounding_box=ImageBox(*item["bounding_box"]),
            track_id=item.get("track_id"),
        )
        for item in document["predictions"]
    )
    return document, detections


def load_actions(path: Path) -> tuple[dict[str, Any], tuple[TemporalAction, ...]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    actions = tuple(
        TemporalAction(
            prediction_id=item["prediction_id"],
            timestamp_ms=item["timestamp_ms"],
            label=item["label"],
            visual_team=item["team"],
            confidence=item["confidence"],
        )
        for item in document["predictions"]
    )
    return document, actions


def summarize(
    actions: tuple[TemporalAction, ...],
    detections: tuple[SpatialDetection, ...],
    policy: CandidateFusionPolicy,
) -> dict[str, Any]:
    decisions = tuple(CandidateFusionService(policy).evaluate(action, detections) for action in actions)
    raw_candidates = [item.candidate for item in decisions if item.candidate is not None]
    candidates, suppressed = suppress_competing_candidates(raw_candidates)
    reason_counts: dict[str, int] = {}
    for decision in decisions:
        for reason in decision.reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "policy": asdict(policy),
        "actions_evaluated": len(actions),
        "raw_candidates": len(raw_candidates),
        "candidates": len(candidates),
        "suppressed_competing_candidates": len(suppressed),
        "ambiguous": sum(item.status.value == "ambiguous" for item in decisions),
        "insufficient_evidence": sum(
            item.status.value == "insufficient_evidence" for item in decisions
        ),
        "reason_counts": reason_counts,
        "candidate_details": [asdict(item) for item in candidates],
        "suppressed_candidate_details": [asdict(item) for item in suppressed],
        "decision_details": [asdict(item) for item in decisions],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roboflow", type=Path)
    parser.add_argument("soccernet", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    spatial_document, detections = load_spatial(args.roboflow)
    action_document, actions = load_actions(args.soccernet)
    if spatial_document["media_sha256"] != action_document["media_sha256"]:
        raise ValueError("Las exportaciones pertenecen a vídeos distintos")

    policies = tuple(
        CandidateFusionPolicy(temporal_tolerance_ms=temporal, image_distance_tolerance=spatial)
        for temporal in (80, 120, 200)
        for spatial in (0.08, 0.12, 0.18)
    )
    results = [summarize(actions, detections, policy) for policy in policies]
    selected = next(
        item
        for item in results
        if item["policy"]["temporal_tolerance_ms"] == 120
        and item["policy"]["image_distance_tolerance"] == 0.12
    )
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "media_sha256": spatial_document["media_sha256"],
        "inputs": {
            "roboflow": str(args.roboflow),
            "soccernet": str(args.soccernet),
            "spatial_predictions": len(detections),
            "temporal_predictions": len(actions),
        },
        "input_artifacts": {
            "roboflow_sha256": file_sha256(args.roboflow),
            "soccernet_sha256": file_sha256(args.soccernet),
        },
        "calibration_basis": {
            "video_fps": spatial_document["video"]["fps"],
            "video_frame_interval_ms": 1000 / spatial_document["video"]["fps"],
            "soccernet_model_fps": action_document["video"]["model_fps"],
            "soccernet_frame_interval_ms": 1000 / action_document["video"]["model_fps"],
            "spatial_unit": "normalized_image_diagonal",
            "field_homography_available": False,
            "identity_evidence_available": False,
        },
        "selected_result": selected,
        "policy_grid": [
            {
                key: value
                for key, value in item.items()
                if key
                not in {
                    "candidate_details",
                    "suppressed_candidate_details",
                    "decision_details",
                }
            }
            for item in results
        ],
        "decision": "experimental_candidates_only",
        "limitations": [
            "La distancia pertenece a la imagen, no a coordenadas calibradas del campo.",
            "SoccerNet no identifica al ejecutor ni entrega posición espacial.",
            "El equipo left/right de SoccerNet no está asociado todavía a la plantilla.",
            "Ningún candidato contiene player_id ni se convierte en MatchEvent.",
            "La validación manual de aciertos y falsos emparejamientos sigue pendiente.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in selected.items()
                if key
                not in {
                    "candidate_details",
                    "suppressed_candidate_details",
                    "decision_details",
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
