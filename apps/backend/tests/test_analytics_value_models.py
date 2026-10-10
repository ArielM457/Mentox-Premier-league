"""xT, xG y VAEP: desactivados sin validación; adaptadores comprobados con referencias."""

from math import radians
from random import Random

import pytest
from analytics_builders import A, Events, metadata

from match_intelligence.adapters.models.expected_goals import (
    LogisticCoefficients,
    LogisticExpectedGoalsModel,
    ShotSample,
    calibration_report,
    coefficients_document,
    fit_logistic_xg,
)
from match_intelligence.adapters.models.expected_threat import (
    ExpectedThreatGrid,
    ExpectedThreatModel,
    TrainingAction,
    grid_document,
    train_expected_threat,
)
from match_intelligence.adapters.models.loader import registry_from_directory, registry_from_documents
from match_intelligence.adapters.models.vaep import VaepFeasibilityModel, to_spadl_actions
from match_intelligence.adapters.sources.synthetic import generate_acceptance_match
from match_intelligence.application.analytics.pipeline import MatchAnalytics, build_snapshot
from match_intelligence.application.analytics.value_models import (
    ModelProvenance,
    ValueModelName,
    ValueModelRegistry,
)
from match_intelligence.domain.analytics.pitch import PitchFrame
from match_intelligence.domain.contracts import EventOutcome

REFERENCE_PROVENANCE = ModelProvenance(
    source="prueba unitaria",
    license="MIT",
    training_data="muestras generadas con coeficientes conocidos",
    version="test-1",
    validation={"reference": "recuperación de coeficientes conocidos"},
)


def test_without_validated_models_the_metrics_are_disabled_not_invented() -> None:
    match = generate_acceptance_match()
    snapshot = build_snapshot(match.metadata, match.events)

    model_metrics = {m.key: m for m in snapshot.metrics if m.origin.value == "value_model"}
    assert set(model_metrics) == {"xt_added", "xg", "vaep"}
    for item in model_metrics.values():
        assert item.available is False and item.value is None and item.unavailable_reason
    candidates = MatchAnalytics().candidates(match.metadata, match.events)
    assert not any(f.key in {"xg", "xt_added"} for c in candidates for f in c.facts)


# --- xT --------------------------------------------------------------------------

def test_xt_value_iteration_matches_the_analytic_reference() -> None:
    """Dos zonas: A mueve a B con éxito la mitad de las veces; B tira con 50 % de gol."""
    actions = (
        [TrainingAction(10, 50, 60, 50, "move", True)] * 50
        + [TrainingAction(10, 50, 60, 50, "move", False)] * 50
        + [TrainingAction(60, 50, None, None, "shot", True)] * 50
        + [TrainingAction(60, 50, None, None, "shot", False)] * 50
    )

    grid = train_expected_threat(actions, length_cells=2, width_cells=1)

    # xT(B) = 1 · 0,5 = 0,5 ; xT(A) = 1 · (50/100) · xT(B) = 0,25
    assert grid.values[0][1] == pytest.approx(0.5)
    assert grid.values[0][0] == pytest.approx(0.25)


def _plausible_grid() -> ExpectedThreatGrid:
    return ExpectedThreatGrid(tuple(
        tuple(round(0.01 + 0.03 * column + (0.04 if column >= 6 and 2 <= row <= 5 else 0), 3) for column in range(8))
        for row in range(8)
    ))


def test_xt_grid_plausibility_and_provenance_gate_the_model() -> None:
    model = ExpectedThreatModel(_plausible_grid(), REFERENCE_PROVENANCE)
    assert model.status().enabled

    reversed_grid = ExpectedThreatGrid(tuple(tuple(reversed(row)) for row in _plausible_grid().values))
    assert not ExpectedThreatModel(reversed_grid, REFERENCE_PROVENANCE).status().enabled

    synthetic_only = ModelProvenance("equipo", "MIT", "partidos synthetic del proyecto", "1")
    status = ExpectedThreatModel(_plausible_grid(), synthetic_only).status()
    assert not status.enabled
    assert any("referencia externa" in reason for reason in status.reasons)


def test_enabled_xt_values_passes_and_appears_in_fast_progressions(tmp_path) -> None:
    (tmp_path / "xt.json").write_text(
        __import__("json").dumps(grid_document(_plausible_grid(), REFERENCE_PROVENANCE)), encoding="utf-8"
    )
    registry = registry_from_directory(tmp_path)
    events = Events()
    events.recovery(10, A, "a-1", (40, 50))
    events.pass_(13, A, "a-1", (40, 50), (55, 50))
    events.pass_(16, A, "a-2", (55, 50), (72, 40))

    assert registry.status(ValueModelName.XT).enabled
    assert not registry.status(ValueModelName.XG).enabled
    candidates = MatchAnalytics(value_models=registry).candidates(metadata(), events.items)
    xt_facts = [f for c in candidates for f in c.facts if f.key == "xt_added"]
    assert [f.source_event_ids for f in xt_facts] == [["evt-002"], ["evt-003"]]
    assert all(f.value > 0 and f.formula_version == "xt@test-1" for f in xt_facts)


# --- xG --------------------------------------------------------------------------

TRUE_XG = LogisticCoefficients(intercept=-0.2, distance_m=-0.12, angle_rad=1.1)


def _shots(count: int, seed: int) -> list[ShotSample]:
    rng = Random(seed)
    samples = []
    for _ in range(count):
        distance = rng.uniform(5, 35)
        angle = radians(rng.uniform(5, 60))
        samples.append(ShotSample(distance, angle, rng.random() < TRUE_XG.probability(distance, angle)))
    return samples


def test_xg_fit_recovers_known_coefficients_and_is_calibrated() -> None:
    fitted = fit_logistic_xg(_shots(6000, seed=11))

    assert fitted.distance_m == pytest.approx(TRUE_XG.distance_m, abs=0.02)
    assert fitted.angle_rad == pytest.approx(TRUE_XG.angle_rad, abs=0.4)
    report = calibration_report(fitted, _shots(3000, seed=12))
    assert report["max_bin_gap"] < 0.05
    assert report["brier"] < 0.2


def test_xg_plausibility_rejects_inverted_models() -> None:
    assert LogisticExpectedGoalsModel(TRUE_XG, REFERENCE_PROVENANCE).status().enabled
    inverted = LogisticCoefficients(intercept=-3, distance_m=0.1, angle_rad=-0.5)
    status = LogisticExpectedGoalsModel(inverted, REFERENCE_PROVENANCE).status()
    assert not status.enabled and len(status.reasons) >= 2


def test_enabled_xg_adds_probability_to_shot_moments_and_team_totals() -> None:
    registry = registry_from_documents({"xg": coefficients_document(TRUE_XG, REFERENCE_PROVENANCE)})
    events = Events()
    close = events.shot(10, A, "a-9", (92, 50), outcome=EventOutcome.SAVED)
    far = events.shot(60, A, "a-9", (65, 50), outcome=EventOutcome.OFF_TARGET)

    snapshot = build_snapshot(metadata(), events.items, value_models=registry)
    total = next(m for m in snapshot.metrics if m.key == "xg" and m.team_id == A)
    frame = PitchFrame.from_metadata(metadata())
    per_shot = [registry.event_metric(ValueModelName.XG, frame, e).value for e in (close, far)]

    assert per_shot[0] > per_shot[1]
    assert total.value == pytest.approx(sum(per_shot), abs=1e-3)
    assert total.source_event_ids == ["evt-001", "evt-002"]
    shot_facts = [
        f for c in MatchAnalytics(value_models=registry).candidates(metadata(), events.items, {"mode": "analyst"})
        for f in c.facts if f.key == "xg"
    ]
    assert shot_facts and shot_facts[0].origin.value == "value_model"


# --- VAEP --------------------------------------------------------------------------

def test_vaep_stays_disabled_and_reports_the_data_gap() -> None:
    match = generate_acceptance_match()
    status = ValueModelRegistry([VaepFeasibilityModel()]).status(ValueModelName.VAEP)
    conversion = to_spadl_actions(PitchFrame.from_metadata(match.metadata), match.events)

    assert not status.enabled
    assert any("bodypart" in reason for reason in status.reasons)
    assert conversion.unsupported_event_ids == ("evt-001", "evt-005", "evt-008")  # presión y cambio de posesión
    assert 0 < conversion.coverage < 1
    assert {action.bodypart_name for action in conversion.actions} == {"unknown"}
