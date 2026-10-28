"""Tablero de demostración: datos del motor real y seguimiento marcado como simulado."""

import json
from pathlib import Path

from analytics_demo import build_demo_data
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario

DEMO = Path(__file__).resolve().parents[3] / "experiments" / "analytics-demo"


def test_demo_data_comes_from_the_engine_and_labels_the_mock() -> None:
    data = build_demo_data()
    match = generate_analytics_scenario()

    assert data["tracking"]["source"] == "simulated_fixture"
    assert len(data["events"]) == len(data["timeline"]) == len(match.events)
    assert [p["key"] for p in data["profiles"]] == ["neutral", "casual", "analyst", "rio_fan", "player_sol"]
    casual = next(p for p in data["profiles"] if p["key"] == "casual")
    emitted = [d[0] for d in casual["decisions"] if d[1] == "e"]
    expected = MatchAnalytics().candidates(match.metadata, match.events, {"mode": "casual"})
    assert emitted == [c.candidate_id for c in expected]
    assert all(cid in data["moments"] for p in data["profiles"] for cid, *_ in p["decisions"])
    json.dumps(data, ensure_ascii=False)


def test_saved_dashboard_contains_current_engine_output() -> None:
    """Si falla, ejecute ``python apps/backend/scripts/export_analytics_demo.py``."""
    page = (DEMO / "tablero.html").read_text(encoding="utf-8")
    data = json.dumps(build_demo_data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    template = (DEMO / "plantilla.html").read_text(encoding="utf-8")

    assert template.replace("__DATOS__", data) in page
