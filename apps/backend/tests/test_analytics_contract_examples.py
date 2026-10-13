"""Ejemplos compartidos con Persona 3 y Persona 4: válidos, mínimos, inválidos y al día."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from analytics_examples import build_examples, render
from match_intelligence.domain.analytics.models import (
    AttentionDecision,
    InsightCandidate,
    MatchSnapshot,
)

EXAMPLES = Path(__file__).resolve().parents[3] / "docs" / "persona-2-estado-y-analitica" / "ejemplos"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("model", "prefix"),
    [(MatchSnapshot, "match-snapshot-v1"), (InsightCandidate, "insight-candidate-v1")],
)
def test_contract_examples_validate_as_documented(model, prefix) -> None:
    model.model_validate(_load(f"{prefix}.valido.json"))
    minimal = model.model_validate(_load(f"{prefix}.sin-opcionales.json"))
    assert minimal.contract_version == "1"
    with pytest.raises(ValidationError):
        model.model_validate(_load(f"{prefix}.invalido.json"))


def test_discarded_decision_example_explains_why() -> None:
    decision = AttentionDecision.model_validate(_load("attention-decision-v1.descartado.json"))

    assert decision.outcome.value == "discarded"
    assert decision.reasons[-1].code == "below_threshold"


def test_examples_are_current_with_the_code() -> None:
    """Si falla, ejecute ``python apps/backend/scripts/export_analytics_examples.py``."""
    for name, value in build_examples().items():
        assert (EXAMPLES / name).read_text(encoding="utf-8") == render(value), name


def test_valid_examples_keep_the_fields_persona_4_reads() -> None:
    snapshot = _load("match-snapshot-v1.valido.json")
    candidate = _load("insight-candidate-v1.valido.json")

    for key in ("contract_version", "match_id", "period", "clock_ms", "video_time_ms", "score",
                "possession_team_id", "metrics", "recent_event_ids"):
        assert key in snapshot
    for key in ("contract_version", "candidate_id", "match_id", "period", "clock_ms", "kind",
                "priority", "team_id", "player_ids", "facts", "source_event_ids", "evidence_limits"):
        assert key in candidate
    for key in ("key", "team_id", "player_id", "value", "available", "unit", "window_ms",
                "formula_version", "source_event_ids"):
        assert key in candidate["facts"][0]
