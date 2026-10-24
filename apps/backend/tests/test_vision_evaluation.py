from dataclasses import replace

import pytest

from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.vision_evaluation import (
    AuthorizedMedia,
    BoundingBox,
    IntegrationDecision,
    ManualObservation,
    ModelConfiguration,
    ModelPrediction,
    PermissionBasis,
    PredictionOrigin,
    VisionEvaluationError,
    VisionExperimentEvaluator,
    VisionTask,
)


def authorized_sample() -> AuthorizedMedia:
    return AuthorizedMedia(
        media_id="project-generated-sample-001",
        sha256="a" * 64,
        duration_ms=10_000,
        permission_basis=PermissionBasis.PROJECT_GENERATED,
        permission_reference="docs/vision/project-generated-sample.md",
    )


def roboflow_configuration(
    origin: PredictionOrigin = PredictionOrigin.SIMULATED_FIXTURE,
) -> ModelConfiguration:
    return ModelConfiguration(
        provider="roboflow-sports",
        model_name="soccer-player-detection",
        model_version="unselected-real-version",
        source_revision="unselected-real-revision",
        task=VisionTask.SPATIAL_DETECTION,
        classes=("player", "ball", "referee"),
        parameters=(("confidence", "0.25"), ("iou_threshold", "0.50")),
        prediction_origin=origin,
    )


def soccernet_configuration(
    origin: PredictionOrigin = PredictionOrigin.SIMULATED_FIXTURE,
) -> ModelConfiguration:
    return ModelConfiguration(
        provider="soccernet-teamspotting",
        model_name="T-DEED-baseline",
        model_version="unselected-real-version",
        source_revision="unselected-real-revision",
        task=VisionTask.ACTION_SPOTTING,
        classes=("pass", "shot", "goal"),
        parameters=(("temporal_tolerance_ms", "1000"),),
        prediction_origin=origin,
    )


def test_media_requires_documented_permission() -> None:
    with pytest.raises(VisionEvaluationError, match="permission_reference"):
        replace(authorized_sample(), permission_reference="")


def test_media_accepts_documented_source_terms() -> None:
    media = replace(
        authorized_sample(),
        permission_basis=PermissionBasis.SOURCE_TERMS,
        permission_reference="https://example.test/source-terms",
    )

    assert media.permission_basis is PermissionBasis.SOURCE_TERMS


def test_model_records_version_classes_revision_and_configuration() -> None:
    model = roboflow_configuration()

    assert model.model_name == "soccer-player-detection"
    assert model.model_version == "unselected-real-version"
    assert model.source_revision == "unselected-real-revision"
    assert model.classes == ("player", "ball", "referee")
    assert dict(model.parameters)["confidence"] == "0.25"


def test_spatial_evaluation_reports_quality_false_positives_and_misses() -> None:
    references = (
        ManualObservation(
            "manual-player", 1_000, "player", BoundingBox(0.1, 0.1, 0.3, 0.5)
        ),
        ManualObservation(
            "manual-ball", 1_000, "ball", BoundingBox(0.6, 0.5, 0.65, 0.55)
        ),
    )
    predictions = (
        ModelPrediction(
            "pred-player",
            1_000,
            "player",
            0.9,
            BoundingBox(0.1, 0.1, 0.3, 0.5),
        ),
        ModelPrediction(
            "pred-referee",
            1_000,
            "referee",
            0.8,
            BoundingBox(0.7, 0.1, 0.8, 0.5),
        ),
    )

    report = VisionExperimentEvaluator().evaluate(
        media=authorized_sample(),
        model=roboflow_configuration(),
        references=references,
        predictions=predictions,
        processing_time_ms=4_000,
    )

    assert report.quality.true_positives == 1
    assert report.quality.false_positives == 1
    assert report.quality.missed == 1
    assert report.quality.precision == 0.5
    assert report.quality.recall == 0.5
    assert report.false_positive_ids == ("pred-referee",)
    assert report.missed_observation_ids == ("manual-ball",)


def test_action_evaluation_uses_temporal_tolerance() -> None:
    references = (
        ManualObservation("manual-pass", 1_000, "pass"),
        ManualObservation("manual-shot", 5_000, "shot"),
    )
    predictions = (
        ModelPrediction("pred-pass", 1_500, "pass", 0.9),
        ModelPrediction("pred-shot-late", 7_000, "shot", 0.8),
        ModelPrediction("pred-goal", 9_000, "goal", 0.7),
    )

    report = VisionExperimentEvaluator().evaluate(
        media=authorized_sample(),
        model=soccernet_configuration(),
        references=references,
        predictions=predictions,
        processing_time_ms=12_000,
        temporal_tolerance_ms=1_000,
    )

    assert report.quality.true_positives == 1
    assert report.false_positive_ids == ("pred-shot-late", "pred-goal")
    assert report.missed_observation_ids == ("manual-shot",)


def test_quality_and_processing_are_reported_separately() -> None:
    report = VisionExperimentEvaluator().evaluate(
        media=authorized_sample(),
        model=soccernet_configuration(),
        references=(ManualObservation("manual-pass", 1_000, "pass"),),
        predictions=(ModelPrediction("pred-pass", 1_000, "pass", 0.9),),
        processing_time_ms=5_000,
    )

    assert report.quality.f1 == 1
    assert report.processing.processing_time_ms == 5_000
    assert report.processing.media_duration_ms == 10_000
    assert report.processing.realtime_factor == 0.5


def test_simulated_predictions_cannot_qualify_a_model_for_the_demo() -> None:
    evaluator = VisionExperimentEvaluator()
    report = evaluator.evaluate(
        media=authorized_sample(),
        model=soccernet_configuration(PredictionOrigin.SIMULATED_FIXTURE),
        references=(ManualObservation("manual-pass", 1_000, "pass"),),
        predictions=(ModelPrediction("pred-pass", 1_000, "pass", 1),),
        processing_time_ms=1,
    )

    assessment = evaluator.assess(
        report,
        minimum_precision=0,
        minimum_recall=0,
        maximum_realtime_factor=10,
    )

    assert assessment.decision is IntegrationDecision.PENDING_REAL_RUN
    assert "no provienen" in assessment.reasons[0]


def test_insufficient_actual_result_is_rejected_with_reasons() -> None:
    evaluator = VisionExperimentEvaluator()
    report = evaluator.evaluate(
        media=authorized_sample(),
        model=soccernet_configuration(PredictionOrigin.ACTUAL_MODEL),
        references=(ManualObservation("manual-shot", 1_000, "shot"),),
        predictions=(ModelPrediction("pred-goal", 1_000, "goal", 0.9),),
        processing_time_ms=20_000,
    )

    assessment = evaluator.assess(
        report,
        minimum_precision=0.8,
        minimum_recall=0.8,
        maximum_realtime_factor=1,
    )

    assert assessment.decision is IntegrationDecision.REJECTED
    assert assessment.reasons == (
        "precisión inferior al umbral",
        "recobrado inferior al umbral",
        "tiempo de procesamiento superior al umbral",
    )


def test_sufficient_actual_result_is_only_marked_as_candidate() -> None:
    evaluator = VisionExperimentEvaluator()
    report = evaluator.evaluate(
        media=authorized_sample(),
        model=soccernet_configuration(PredictionOrigin.ACTUAL_MODEL),
        references=(ManualObservation("manual-pass", 1_000, "pass"),),
        predictions=(ModelPrediction("pred-pass", 1_000, "pass", 0.9),),
        processing_time_ms=5_000,
    )

    assessment = evaluator.assess(
        report,
        minimum_precision=0.8,
        minimum_recall=0.8,
        maximum_realtime_factor=1,
    )

    assert assessment.decision is IntegrationDecision.CANDIDATE
    assert assessment.reasons == ()


def test_comparison_keeps_task_specific_reports_and_synthetic_fallback() -> None:
    evaluator = VisionExperimentEvaluator()
    media = authorized_sample()
    roboflow_report = evaluator.evaluate(
        media=media,
        model=roboflow_configuration(),
        references=(
            ManualObservation(
                "manual-player", 1_000, "player", BoundingBox(0, 0, 0.2, 0.5)
            ),
        ),
        predictions=(
            ModelPrediction(
                "pred-player", 1_000, "player", 1, BoundingBox(0, 0, 0.2, 0.5)
            ),
        ),
        processing_time_ms=1_000,
    )
    soccer_report = evaluator.evaluate(
        media=media,
        model=soccernet_configuration(),
        references=(ManualObservation("manual-pass", 1_000, "pass"),),
        predictions=(ModelPrediction("pred-pass", 1_000, "pass", 1),),
        processing_time_ms=1_000,
    )
    assessments = tuple(
        evaluator.assess(
            report,
            minimum_precision=0.8,
            minimum_recall=0.8,
            maximum_realtime_factor=1,
        )
        for report in (roboflow_report, soccer_report)
    )

    comparison = evaluator.compare((roboflow_report, soccer_report), assessments)

    assert {report.model.task for report in comparison.reports} == {
        VisionTask.SPATIAL_DETECTION,
        VisionTask.ACTION_SPOTTING,
    }
    assert comparison.synthetic_flow_required
    assert all(
        item.decision is IntegrationDecision.PENDING_REAL_RUN
        for item in comparison.assessments
    )


def test_undeclared_prediction_class_is_rejected() -> None:
    with pytest.raises(VisionEvaluationError, match="Clases no declaradas"):
        VisionExperimentEvaluator().evaluate(
            media=authorized_sample(),
            model=soccernet_configuration(),
            references=(),
            predictions=(ModelPrediction("pred-foul", 1_000, "foul", 0.9),),
            processing_time_ms=1_000,
        )


def test_evaluation_failure_does_not_block_the_synthetic_match() -> None:
    evaluator = VisionExperimentEvaluator()

    with pytest.raises(VisionEvaluationError):
        evaluator.evaluate(
            media=authorized_sample(),
            model=soccernet_configuration(),
            references=(),
            predictions=(ModelPrediction("pred-foul", 1_000, "foul", 0.9),),
            processing_time_ms=1_000,
        )

    match = generate_acceptance_match()
    assert len(match.events) == 10
