"""Evalúa predicciones exportadas mediante el contrato de DV-US-11."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from match_intelligence.application.vision_evaluation import (
    AuthorizedMedia,
    BoundingBox,
    ManualObservation,
    ModelConfiguration,
    ModelPrediction,
    PermissionBasis,
    PredictionOrigin,
    VisionExperimentEvaluator,
    VisionTask,
)


def bounding_box(value: list[float] | None) -> BoundingBox | None:
    if value is None:
        return None
    if len(value) != 4:
        raise ValueError("bounding_box debe contener [x_min, y_min, x_max, y_max]")
    return BoundingBox(*value)


def evaluate_document(document: dict[str, Any]) -> dict[str, Any]:
    media_data = document["media"]
    model_data = document["model"]
    media = AuthorizedMedia(
        media_id=media_data["media_id"],
        sha256=media_data["sha256"],
        duration_ms=media_data["duration_ms"],
        permission_basis=PermissionBasis(media_data["permission_basis"]),
        permission_reference=media_data["permission_reference"],
    )
    model = ModelConfiguration(
        provider=model_data["provider"],
        model_name=model_data["model_name"],
        model_version=model_data["model_version"],
        source_revision=model_data["source_revision"],
        task=VisionTask(model_data["task"]),
        classes=tuple(model_data["classes"]),
        parameters=tuple(sorted(model_data["parameters"].items())),
        prediction_origin=PredictionOrigin(model_data["prediction_origin"]),
    )
    references = tuple(
        ManualObservation(
            observation_id=item["observation_id"],
            timestamp_ms=item["timestamp_ms"],
            label=item["label"],
            bounding_box=bounding_box(item.get("bounding_box")),
        )
        for item in document["references"]
    )
    predictions = tuple(
        ModelPrediction(
            prediction_id=item["prediction_id"],
            timestamp_ms=item["timestamp_ms"],
            label=item["label"],
            confidence=item["confidence"],
            bounding_box=bounding_box(item.get("bounding_box")),
        )
        for item in document["predictions"]
    )
    evaluator = VisionExperimentEvaluator()
    report = evaluator.evaluate(
        media=media,
        model=model,
        references=references,
        predictions=predictions,
        processing_time_ms=document["processing_time_ms"],
        temporal_tolerance_ms=document.get("temporal_tolerance_ms", 1_000),
        iou_threshold=document.get("iou_threshold", 0.5),
    )
    thresholds = document["integration_thresholds"]
    assessment = evaluator.assess(
        report,
        minimum_precision=thresholds["minimum_precision"],
        minimum_recall=thresholds["minimum_recall"],
        maximum_realtime_factor=thresholds["maximum_realtime_factor"],
    )
    report_document = asdict(report)
    report_document["processing"]["realtime_factor"] = (
        report.processing.realtime_factor
    )
    return {"report": report_document, "assessment": asdict(assessment)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara predicciones de visión con anotaciones manuales"
    )
    parser.add_argument("input", type=Path, help="Documento JSON del experimento")
    parser.add_argument("--output", type=Path, help="Ruta opcional del informe JSON")
    args = parser.parse_args()

    document = json.loads(args.input.read_text(encoding="utf-8"))
    result = json.dumps(evaluate_document(document), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
