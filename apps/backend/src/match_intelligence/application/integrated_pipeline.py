"""Consulta unificada de las salidas reales de visión y fusión."""

from dataclasses import dataclass
from functools import cached_property
import hashlib
import json
import os
from pathlib import Path
from typing import Any


class PipelineArtifactError(RuntimeError):
    """Los artefactos requeridos no existen o no pertenecen al mismo medio."""


@dataclass(frozen=True, slots=True)
class PipelinePaths:
    roboflow: Path
    soccernet: Path
    fusion: Path
    video: Path

    @classmethod
    def from_repository(cls, root: Path) -> "PipelinePaths":
        return cls(
            roboflow=Path(
                os.getenv(
                    "MENTOX_ROBOFLOW_ARTIFACT",
                    root / "experiments/roboflow-sports/output-real/roboflow-sports-predictions.json",
                )
            ),
            soccernet=Path(
                os.getenv(
                    "MENTOX_SOCCERNET_ARTIFACT",
                    root / "experiments/soccernet-teamspotting/output-real/soccernet-predictions.json",
                )
            ),
            fusion=Path(
                os.getenv(
                    "MENTOX_FUSION_ARTIFACT",
                    root / "experiments/fusion-calibration/output/dv-us-21-report.json",
                )
            ),
            video=Path(
                os.getenv(
                    "MENTOX_INTEGRATION_VIDEO",
                    root / "experiments/authorized-video/input/2e57b9_0.mp4",
                )
            ),
        )


class IntegratedPipeline:
    """Lee una sola vez los resultados y ofrece ventanas sincronizadas."""

    def __init__(self, paths: PipelinePaths) -> None:
        self.paths = paths

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise PipelineArtifactError(f"No existe el artefacto requerido: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise PipelineArtifactError(f"No se pudo leer {path}: {error}") from error

    @cached_property
    def roboflow(self) -> dict[str, Any]:
        return self._load(self.paths.roboflow)

    @cached_property
    def soccernet(self) -> dict[str, Any]:
        return self._load(self.paths.soccernet)

    @cached_property
    def fusion(self) -> dict[str, Any]:
        return self._load(self.paths.fusion)

    @cached_property
    def media_sha256(self) -> str:
        hashes = {
            self.roboflow["media_sha256"],
            self.soccernet["media_sha256"],
            self.fusion["media_sha256"],
        }
        if len(hashes) != 1:
            raise PipelineArtifactError("Los resultados pertenecen a medios distintos")
        self._validate_fusion_inputs()
        return hashes.pop()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise PipelineArtifactError(f"No se pudo calcular SHA-256 de {path}: {error}") from error
        return digest.hexdigest()

    def _validate_fusion_inputs(self) -> None:
        """Impide combinar un informe de fusión viejo con predicciones nuevas."""
        recorded_artifacts = self.fusion.get("input_artifacts")
        if recorded_artifacts is not None:
            expected = {
                "roboflow_sha256": self._sha256(self.paths.roboflow),
                "soccernet_sha256": self._sha256(self.paths.soccernet),
            }
            if any(recorded_artifacts.get(key) != value for key, value in expected.items()):
                raise PipelineArtifactError(
                    "El informe de fusión no corresponde a los archivos de predicciones actuales"
                )
            return

        inputs = self.fusion.get("inputs", {})
        if inputs.get("spatial_predictions") != len(self.roboflow.get("predictions", [])) or inputs.get(
            "temporal_predictions"
        ) != len(self.soccernet.get("predictions", [])):
            raise PipelineArtifactError(
                "El informe de fusión antiguo no corresponde a las predicciones actuales"
            )

        spatial_ids = {
            item.get("prediction_id") for item in self.roboflow.get("predictions", [])
        }
        temporal_ids = {
            item.get("prediction_id") for item in self.soccernet.get("predictions", [])
        }
        for candidate in self.fusion.get("selected_result", {}).get("candidate_details", []):
            action_id = candidate.get("action", {}).get("prediction_id")
            ball_id = candidate.get("ball", {}).get("prediction_id")
            player_id = candidate.get("player", {}).get("prediction_id")
            if action_id not in temporal_ids or ball_id not in spatial_ids or player_id not in spatial_ids:
                raise PipelineArtifactError(
                    "El informe de fusión antiguo referencia predicciones inexistentes"
                )

    def status(self) -> dict[str, Any]:
        selected = self.fusion["selected_result"]
        return {
            "status": "ready",
            "media_sha256": self.media_sha256,
            "video_available": self.paths.video.is_file(),
            "duration_ms": self.roboflow["video"]["duration_ms"],
            "roboflow": {
                "status": "completed",
                "predictions": len(self.roboflow["predictions"]),
                "pitch_observations": len(
                    self.roboflow.get("pitch_observations", [])
                ),
                "models": sorted(self.roboflow.get("models", {})),
                "frames_processed": self.roboflow["video"]["frames_processed"],
                "processing_time_ms": self.roboflow["processing_time_ms"],
            },
            "soccernet": {
                "status": "completed",
                "predictions": len(self.soccernet["predictions"]),
                "frames_processed": self.soccernet["video"]["model_frames"],
                "processing_time_ms": self.soccernet["processing_time_ms"],
            },
            "fusion": {
                "status": "experimental_candidates_only",
                "actions_evaluated": selected["actions_evaluated"],
                "candidates": selected["candidates"],
                "match_events_published": 0,
            },
        }

    def timeline(self, *, start_ms: int, end_ms: int, spatial_limit: int = 100) -> dict[str, Any]:
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError("La ventana temporal es inválida")
        spatial = [
            item
            for item in self.roboflow["predictions"]
            if start_ms <= item["timestamp_ms"] <= end_ms
        ]
        pitch = [
            item
            for item in self.roboflow.get("pitch_observations", [])
            if start_ms <= item["timestamp_ms"] <= end_ms
        ]
        actions = [
            item
            for item in self.soccernet["predictions"]
            if start_ms <= item["timestamp_ms"] <= end_ms
        ]
        candidates = [
            item
            for item in self.fusion["selected_result"]["candidate_details"]
            if start_ms <= item["action"]["timestamp_ms"] <= end_ms
        ]
        return {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "spatial_total": len(spatial),
            "spatial_truncated": len(spatial) > spatial_limit,
            "spatial_observations": spatial[:spatial_limit],
            "pitch_observations": pitch,
            "temporal_actions": actions,
            "fusion_candidates": candidates,
            "notice": "Los candidatos son experimentales y no son MatchEvent.",
        }
