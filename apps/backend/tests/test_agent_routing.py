import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_intelligence.application.routing import (
    AgentOrchestrator,
    AgentRoutingService,
    FixtureDispatchGateway,
    RoutingEvaluationRequest,
)
from match_intelligence.application.routing.orchestrator import DispatchProposal
from match_intelligence.main import app


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "agent-routing-scenarios.json").read_text(
        encoding="utf-8"
    )
)


def request_for(scenario: dict) -> RoutingEvaluationRequest:
    return RoutingEvaluationRequest.model_validate(
        {
            "match_id": FIXTURE["match_id"],
            "events": scenario.get("input_events", []),
            "control_signal": scenario.get("control_signal"),
            "preferences": {"language": "es", "mode": "casual", "level": "normal"},
        }
    )


@pytest.mark.parametrize(
    "scenario",
    FIXTURE["scenarios"],
    ids=[item["scenario_id"] for item in FIXTURE["scenarios"]],
)
def test_synthetic_scenarios_take_expected_route(scenario):
    result = AgentRoutingService().evaluate(request_for(scenario))
    assert result.decision.route == scenario["expected_route"]
    if scenario["expected_agent"] is None:
        assert result.agent_request is None
        assert result.dispatch is None
    else:
        assert result.agent_request.task == scenario["expected_agent"]
        assert result.dispatch.target_agent == scenario["expected_agent"]
    if "expected_window_ms" in scenario:
        assert result.agent_request.ttl_ms == scenario["expected_window_ms"]
    if "expected_editorial_status" in scenario:
        assert result.agent_request.task == "recap"


def test_metrics_only_never_reaches_orchestrator():
    scenario = FIXTURE["scenarios"][0]
    result = AgentRoutingService().evaluate(request_for(scenario))
    assert result.metric_updates[0].key == "passes"
    assert result.metric_updates[0].source_event_ids == ["evt-001"]
    assert result.agent_request is None
    assert result.dispatch is None


def test_duplicate_is_ignored_without_recounting():
    scenario = FIXTURE["scenarios"][0]
    payload = request_for(scenario).model_dump()
    payload["existing_event_ids"] = ["evt-001"]
    result = AgentRoutingService().evaluate(RoutingEvaluationRequest.model_validate(payload))
    assert result.decision.route == "rejected"
    assert result.metric_updates == []
    assert result.ignored_event_ids == ["evt-001"]


def test_progression_context_is_compact_and_traceable():
    scenario = FIXTURE["scenarios"][1]
    result = AgentRoutingService().evaluate(request_for(scenario))
    assert result.play_context.pattern_key == "recovery_and_fast_progression"
    assert result.play_context.match_status == "confirmed"
    assert result.agent_request.source_event_ids == ["evt-010", "evt-011", "evt-012"]
    assert not hasattr(result.agent_request, "events")


def test_http_route_exposes_filter_result():
    scenario = FIXTURE["scenarios"][2]
    response = TestClient(app).post(
        "/api/v1/agent-routing/evaluate",
        json=request_for(scenario).model_dump(mode="json"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["route"] == "danger_immediate"
    assert body["dispatch"]["target_agent"] == "danger_simulation"
    assert body["agent_request"]["source_event_ids"] == [
        "evt-010",
        "evt-011",
        "evt-012",
        "evt-020",
    ]


class WrongDispatchGateway:
    def route(self, request):
        return DispatchProposal(target_agent="narrator", reason="wrong route")


def test_orchestrator_cannot_change_supported_task():
    danger = AgentRoutingService().evaluate(request_for(FIXTURE["scenarios"][2]))
    with pytest.raises(ValueError):
        AgentOrchestrator(WrongDispatchGateway()).dispatch(danger.agent_request)


def test_same_input_produces_same_decision_and_dispatch():
    request = request_for(FIXTURE["scenarios"][2])
    first = AgentRoutingService().evaluate(request)
    second = AgentRoutingService().evaluate(request)
    assert first == second
    assert first.dispatch.idempotency_key == second.dispatch.idempotency_key
