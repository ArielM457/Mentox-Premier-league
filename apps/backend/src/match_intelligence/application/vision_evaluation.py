from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
import re


class VisionTask(StrEnum):
    SPATIAL_DETECTION = "spatial_detection"
    ACTION_SPOTTING = "action_spotting"


class PredictionOrigin(StrEnum):
    ACTUAL_MODEL = "actual_model"
    SIMULATED_FIXTURE = "simulated_fixture"


class PermissionBasis(StrEnum):
    PROJECT_GENERATED = "project_generated"
    WRITTEN_AUTHORIZATION = "written_authorization"
    SOURCE_TERMS = "source_terms"


class IntegrationDecision(StrEnum):
    CANDIDATE = "candidate"
    REJECTED = "rejected"
    PENDING_REAL_RUN = "pending_real_run"


class VisionEvaluationError(ValueError):
    """La entrada no permite producir una evaluación trazable."""


@dataclass(frozen=True, slots=True)
class AuthorizedMedia:
    media_id: str
    sha256: str
    duration_ms: int
    permission_basis: PermissionBasis
    permission_reference: str

    def __post_init__(self) -> None:
        if not self.media_id.strip():
            raise VisionEvaluationError("media_id es obligatorio")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise VisionEvaluationError("sha256 debe tener 64 caracteres hexadecimales")
        if self.duration_ms <= 0:
            raise VisionEvaluationError("duration_ms debe ser mayor que cero")
        if not self.permission_reference.strip():
            raise VisionEvaluationError("permission_reference es obligatoria")


@dataclass(frozen=True, slots=True)
class ModelConfiguration:
    provider: str
    model_name: str
    model_version: str
    source_revision: str
    task: VisionTask
    classes: tuple[str, ...]
    parameters: tuple[tuple[str, str], ...]
    prediction_origin: PredictionOrigin

    def __post_init__(self) -> None:
        required = {
            "provider": self.provider,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "source_revision": self.source_revision,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise VisionEvaluationError(
                "Faltan metadatos del modelo: " + ", ".join(missing)
            )
        if not self.classes or any(not label.strip() for label in self.classes):
            raise VisionEvaluationError("classes debe declarar al menos una clase")
        if len(set(self.classes)) != len(self.classes):
            raise VisionEvaluationError("classes no puede contener duplicados")
        parameter_names = [name for name, _ in self.parameters]
        if any(not name.strip() for name in parameter_names):
            raise VisionEvaluationError("Cada parámetro debe tener nombre")
        if len(set(parameter_names)) != len(parameter_names):
            raise VisionEvaluationError("Los parámetros no pueden repetirse")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        values = (self.x_min, self.y_min, self.x_max, self.y_max)
        if any(not isfinite(value) or value < 0 or value > 1 for value in values):
            raise VisionEvaluationError("Las coordenadas deben estar entre 0 y 1")
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise VisionEvaluationError("La caja debe tener área positiva")

    def intersection_over_union(self, other: "BoundingBox") -> float:
        width = max(0.0, min(self.x_max, other.x_max) - max(self.x_min, other.x_min))
        height = max(0.0, min(self.y_max, other.y_max) - max(self.y_min, other.y_min))
        intersection = width * height
        own_area = (self.x_max - self.x_min) * (self.y_max - self.y_min)
        other_area = (other.x_max - other.x_min) * (other.y_max - other.y_min)
        return intersection / (own_area + other_area - intersection)


@dataclass(frozen=True, slots=True)
class ManualObservation:
    observation_id: str
    timestamp_ms: int
    label: str
    bounding_box: BoundingBox | None = None


@dataclass(frozen=True, slots=True)
class ModelPrediction:
    prediction_id: str
    timestamp_ms: int
    label: str
    confidence: float
    bounding_box: BoundingBox | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or not isfinite(self.confidence):
            raise VisionEvaluationError("confidence debe estar entre 0 y 1")


@dataclass(frozen=True, slots=True)
class ProcessingMeasurement:
    processing_time_ms: float
    media_duration_ms: int

    def __post_init__(self) -> None:
        if not isfinite(self.processing_time_ms) or self.processing_time_ms <= 0:
            raise VisionEvaluationError("processing_time_ms debe ser mayor que cero")
        if self.media_duration_ms <= 0:
            raise VisionEvaluationError("media_duration_ms debe ser mayor que cero")

    @property
    def realtime_factor(self) -> float:
        return self.processing_time_ms / self.media_duration_ms


@dataclass(frozen=True, slots=True)
class QualityMetrics:
    true_positives: int
    false_positives: int
    missed: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True, slots=True)
class VisionEvaluationReport:
    media: AuthorizedMedia
    model: ModelConfiguration
    quality: QualityMetrics
    processing: ProcessingMeasurement
    false_positive_ids: tuple[str, ...]
    missed_observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelAssessment:
    provider: str
    decision: IntegrationDecision
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VisionComparison:
    reports: tuple[VisionEvaluationReport, ...]
    assessments: tuple[ModelAssessment, ...]
    synthetic_flow_required: bool = True


class VisionExperimentEvaluator:
    """Evalúa predicciones exportadas sin cargar modelos dentro del MVP."""

    def evaluate(
        self,
        *,
        media: AuthorizedMedia,
        model: ModelConfiguration,
        references: tuple[ManualObservation, ...],
        predictions: tuple[ModelPrediction, ...],
        processing_time_ms: float,
        temporal_tolerance_ms: int = 1_000,
        iou_threshold: float = 0.5,
    ) -> VisionEvaluationReport:
        self._validate_inputs(
            media=media,
            model=model,
            references=references,
            predictions=predictions,
            temporal_tolerance_ms=temporal_tolerance_ms,
            iou_threshold=iou_threshold,
        )
        matched_predictions: set[int] = set()
        missed: list[str] = []

        for reference in references:
            candidates: list[tuple[float, int]] = []
            for index, prediction in enumerate(predictions):
                if index in matched_predictions or prediction.label != reference.label:
                    continue
                score = self._match_score(
                    model.task,
                    reference,
                    prediction,
                    temporal_tolerance_ms=temporal_tolerance_ms,
                    iou_threshold=iou_threshold,
                )
                if score is not None:
                    candidates.append((score, index))

            if not candidates:
                missed.append(reference.observation_id)
                continue
            _, best_index = min(candidates)
            matched_predictions.add(best_index)

        false_positives = tuple(
            prediction.prediction_id
            for index, prediction in enumerate(predictions)
            if index not in matched_predictions
        )
        true_positives = len(matched_predictions)
        quality = self._quality(
            true_positives=true_positives,
            false_positives=len(false_positives),
            missed=len(missed),
        )
        return VisionEvaluationReport(
            media=media,
            model=model,
            quality=quality,
            processing=ProcessingMeasurement(
                processing_time_ms=processing_time_ms,
                media_duration_ms=media.duration_ms,
            ),
            false_positive_ids=false_positives,
            missed_observation_ids=tuple(missed),
        )

    @staticmethod
    def assess(
        report: VisionEvaluationReport,
        *,
        minimum_precision: float,
        minimum_recall: float,
        maximum_realtime_factor: float,
    ) -> ModelAssessment:
        thresholds = (minimum_precision, minimum_recall, maximum_realtime_factor)
        if any(not isfinite(value) or value < 0 for value in thresholds):
            raise VisionEvaluationError("Los umbrales deben ser finitos y no negativos")
        if minimum_precision > 1 or minimum_recall > 1:
            raise VisionEvaluationError("Los umbrales de calidad no pueden superar 1")

        if report.model.prediction_origin is not PredictionOrigin.ACTUAL_MODEL:
            return ModelAssessment(
                provider=report.model.provider,
                decision=IntegrationDecision.PENDING_REAL_RUN,
                reasons=("Las predicciones no provienen de una ejecución real del modelo",),
            )

        reasons: list[str] = []
        if report.quality.precision < minimum_precision:
            reasons.append("precisión inferior al umbral")
        if report.quality.recall < minimum_recall:
            reasons.append("recobrado inferior al umbral")
        if report.processing.realtime_factor > maximum_realtime_factor:
            reasons.append("tiempo de procesamiento superior al umbral")
        return ModelAssessment(
            provider=report.model.provider,
            decision=(
                IntegrationDecision.REJECTED
                if reasons
                else IntegrationDecision.CANDIDATE
            ),
            reasons=tuple(reasons),
        )

    @staticmethod
    def compare(
        reports: tuple[VisionEvaluationReport, ...],
        assessments: tuple[ModelAssessment, ...],
    ) -> VisionComparison:
        report_providers = {report.model.provider for report in reports}
        assessment_providers = {assessment.provider for assessment in assessments}
        if len(report_providers) != len(reports):
            raise VisionEvaluationError("Cada proveedor debe tener un solo informe")
        if report_providers != assessment_providers:
            raise VisionEvaluationError("Cada informe debe tener una evaluación de integración")
        return VisionComparison(reports=reports, assessments=assessments)

    @staticmethod
    def _match_score(
        task: VisionTask,
        reference: ManualObservation,
        prediction: ModelPrediction,
        *,
        temporal_tolerance_ms: int,
        iou_threshold: float,
    ) -> float | None:
        time_delta = abs(prediction.timestamp_ms - reference.timestamp_ms)
        if time_delta > temporal_tolerance_ms:
            return None
        if task is VisionTask.ACTION_SPOTTING:
            return float(time_delta)

        assert reference.bounding_box is not None
        assert prediction.bounding_box is not None
        iou = reference.bounding_box.intersection_over_union(prediction.bounding_box)
        if iou < iou_threshold:
            return None
        return 1 - iou

    @staticmethod
    def _quality(
        *, true_positives: int, false_positives: int, missed: int
    ) -> QualityMetrics:
        precision_denominator = true_positives + false_positives
        recall_denominator = true_positives + missed
        precision = true_positives / precision_denominator if precision_denominator else 0.0
        recall = true_positives / recall_denominator if recall_denominator else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return QualityMetrics(
            true_positives=true_positives,
            false_positives=false_positives,
            missed=missed,
            precision=precision,
            recall=recall,
            f1=f1,
        )

    @staticmethod
    def _validate_inputs(
        *,
        media: AuthorizedMedia,
        model: ModelConfiguration,
        references: tuple[ManualObservation, ...],
        predictions: tuple[ModelPrediction, ...],
        temporal_tolerance_ms: int,
        iou_threshold: float,
    ) -> None:
        if temporal_tolerance_ms < 0:
            raise VisionEvaluationError("temporal_tolerance_ms no puede ser negativo")
        if not 0 <= iou_threshold <= 1:
            raise VisionEvaluationError("iou_threshold debe estar entre 0 y 1")
        allowed_labels = set(model.classes)
        labels = {item.label for item in (*references, *predictions)}
        unknown = sorted(labels - allowed_labels)
        if unknown:
            raise VisionEvaluationError("Clases no declaradas: " + ", ".join(unknown))

        identifiers = [item.observation_id for item in references]
        identifiers.extend(item.prediction_id for item in predictions)
        if any(not identifier.strip() for identifier in identifiers):
            raise VisionEvaluationError("Todos los registros necesitan identificador")
        if len(set(identifiers)) != len(identifiers):
            raise VisionEvaluationError("Los identificadores deben ser únicos")
        timestamps = [item.timestamp_ms for item in (*references, *predictions)]
        if any(timestamp < 0 or timestamp > media.duration_ms for timestamp in timestamps):
            raise VisionEvaluationError("Los tiempos deben estar dentro del medio")

        if model.task is VisionTask.SPATIAL_DETECTION:
            if any(item.bounding_box is None for item in (*references, *predictions)):
                raise VisionEvaluationError("La evaluación espacial requiere bounding_box")
        elif any(item.bounding_box is not None for item in (*references, *predictions)):
            raise VisionEvaluationError("La evaluación temporal no usa bounding_box")
