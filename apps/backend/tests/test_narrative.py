import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from match_intelligence.application.narrative import (
    ErrorReport,
    InsightCandidate,
    MatchSnapshot,
    NarrativeDraft,
    NarrativeRequest,
    NarrativeService,
    QuestionRequest,
    SummaryRequest,
    ViewerPreferences,
)
from match_intelligence.application.narrative.gateway import FixtureGateway, NarrativePlan
from match_intelligence.adapters.http.schemas import MatchEvent


@pytest.fixture
def sample():
    data = json.loads((Path(__file__).parent / "fixtures" / "narrative_match.json").read_text())
    events = [MatchEvent.model_validate(item) for item in data["events"]]
    source_ids = {event.event_id for event in events}
    assert all(set(item["source_event_ids"]) <= source_ids for item in data["candidates"])
    return (
        MatchSnapshot.model_validate(data["snapshot"]),
        [InsightCandidate.model_validate(item) for item in data["candidates"]],
    )


def test_contract_rejects_bad_sources_and_mixed_matches(sample):
    snapshot, candidates = sample
    assert snapshot.metrics[0].formula_version == "1"
    assert candidates[0].selection_reason
    invalid = candidates[0].model_dump()
    invalid["facts"][0]["source_event_ids"] = ["unknown"]
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(invalid)
    with pytest.raises(ValidationError):
        NarrativeRequest(
            snapshot=snapshot.model_copy(update={"match_id": "other"}),
            candidate=candidates[0],
            preferences=ViewerPreferences(),
        )


def test_minimal_and_invalid_candidate_examples():
    fixture_dir = Path(__file__).parent / "fixtures"
    minimal = json.loads((fixture_dir / "candidate_minimal.json").read_text())
    invalid = json.loads((fixture_dir / "candidate_invalid.json").read_text())
    assert InsightCandidate.model_validate(minimal).evidence_limits == []
    with pytest.raises(ValidationError):
        InsightCandidate.model_validate(invalid)


def test_draft_examples_and_editorial_contract():
    fixture_dir = Path(__file__).parent / "fixtures"
    valid = NarrativeDraft.model_validate(json.loads((fixture_dir / "draft_valid.json").read_text()))
    minimal = NarrativeDraft.model_validate(json.loads((fixture_dir / "draft_minimal.json").read_text()))
    assert valid.publishable
    assert minimal.claims == []
    with pytest.raises(ValidationError):
        NarrativeDraft.model_validate(json.loads((fixture_dir / "draft_invalid.json").read_text()))


def test_languages_modes_and_evidence_limits(sample):
    snapshot, candidates = sample
    service = NarrativeService(FixtureGateway())
    casual = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=ViewerPreferences()))
    analyst = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=ViewerPreferences(language="en", mode="analyst", level="advanced")))
    assert casual.draft.publishable
    assert analyst.draft.publishable
    assert len(casual.draft.claims) == 1
    assert len(analyst.draft.claims) == 2
    assert casual.draft.claims[0].value == analyst.draft.claims[0].value
    assert "causa táctica" in casual.draft.explanation
    assert "tactical cause" in analyst.draft.explanation
    assert analyst.draft.source_event_ids == ["evt-101", "evt-102", "evt-103"]
    goal = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[1], preferences=ViewerPreferences()))
    assert goal.draft.claims[0].key == "goals"
    assert goal.draft.source_event_ids == ["evt-105"]


def test_professional_analyst_forces_advanced_detail(sample):
    snapshot, candidates = sample
    preferences = ViewerPreferences(mode="professional_analyst", level="simple")
    result = NarrativeService(FixtureGateway()).create_live(
        NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=preferences)
    )

    assert preferences.level == "advanced"
    assert result.draft.mode == "professional_analyst"
    assert result.draft.level == "advanced"
    assert len(result.draft.claims) == 2


@pytest.mark.parametrize(
    ("language", "expected"),
    [("de", "Balleroberung"), ("zh", "夺回球权"), ("hi", "गेंद वापसी"), ("fr", "récupération"), ("pt", "recuperação")],
)
def test_additional_languages_render_live_facts(sample, language, expected):
    snapshot, candidates = sample
    result = NarrativeService(FixtureGateway()).create_live(
        NarrativeRequest(
            snapshot=snapshot,
            candidate=candidates[0],
            preferences=ViewerPreferences(language=language, mode="player", level="advanced", favorite_player_id="player-7"),
        )
    )

    assert result.draft.publishable
    assert expected in result.draft.explanation


def test_player_preference_and_no_update(sample):
    snapshot, candidates = sample
    service = NarrativeService(FixtureGateway())
    pref = ViewerPreferences(mode="player", favorite_player_id="player-7")
    result = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=pref))
    assert result.draft.claims[0].player_id == "player-7"
    absent = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=ViewerPreferences(mode="player", favorite_player_id="player-9")))
    assert "Sin novedades" in absent.draft.headline
    assert absent.draft.claims == []


def test_unknown_question_admits_insufficient_data(sample):
    snapshot, candidates = sample
    result = NarrativeService(FixtureGateway()).answer(QuestionRequest(snapshot=snapshot, candidates=candidates, preferences=ViewerPreferences(), question="¿Cuál fue la velocidad del balón?"))
    assert result.draft.verification_status == "approved"
    assert "No se puede determinar" in result.draft.explanation
    assert not result.draft.claims


def test_question_uses_matching_team_and_player_evidence(sample):
    snapshot, candidates = sample
    result = NarrativeService(FixtureGateway()).answer(QuestionRequest(snapshot=snapshot, candidates=candidates, preferences=ViewerPreferences(mode="player", favorite_player_id="player-7"), question="¿Cuántas recuperaciones tiene player-7?"))
    assert len(result.draft.claims) == 1
    assert result.draft.claims[0].key == "recoveries"
    assert result.draft.source_event_ids == ["evt-103"]


def test_summary_requires_editorial_approval(sample):
    snapshot, candidates = sample
    result = NarrativeService(FixtureGateway()).summarize(SummaryRequest(snapshot=snapshot, candidates=candidates, preferences=ViewerPreferences(), match_finished=True))
    assert result.draft.content_kind == "final"
    assert result.draft.editorial_status == "pending"
    assert not result.draft.publishable
    assert result.draft.model_copy(update={"editorial_status": "approved"}).publishable
    wrong_score = snapshot.model_copy(update={"score": {"team-a": 2, "team-b": 0}})
    inconsistent = NarrativeService(FixtureGateway()).summarize(SummaryRequest(snapshot=wrong_score, candidates=candidates, preferences=ViewerPreferences(), match_finished=True))
    assert inconsistent.draft is None
    assert inconsistent.decision.action == "rejected"


def test_valid_and_false_error_reports(sample):
    snapshot, candidates = sample
    service = NarrativeService(FixtureGateway())
    original = service.create_live(NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=ViewerPreferences())).draft
    false_report = service.resolve_report(ErrorReport(report_id="r1", draft=original, reason="Parece incorrecto", snapshot=snapshot, candidate=candidates[0]))
    assert false_report.status == "no_error"
    wrong = original.model_copy(deep=True)
    wrong.claims[0].value = 99
    valid_report = service.resolve_report(ErrorReport(report_id="r2", draft=wrong, reason="Cifra incorrecta", snapshot=snapshot, candidate=candidates[0]))
    assert valid_report.status == "confirmed_error"
    assert valid_report.correction.original_draft_id == original.draft_id
    assert valid_report.correction.claims[0].value == 2
    invented = original.model_copy(update={"explanation": "La defensa rival se desorganizó."})
    text_report = service.resolve_report(ErrorReport(report_id="r3", draft=invented, reason="Causa inventada", snapshot=snapshot, candidate=candidates[0]))
    assert text_report.status == "confirmed_error"


class BadGateway:
    def plan(self, *args, **kwargs):
        return NarrativePlan(fact_indexes=[99], angle="observed")


class FailingGateway:
    def plan(self, *args, **kwargs):
        raise TimeoutError("model did not answer")


def test_unsupported_and_failed_agents_do_not_publish(sample):
    snapshot, candidates = sample
    request = NarrativeRequest(snapshot=snapshot, candidate=candidates[0], preferences=ViewerPreferences())
    rejected = NarrativeService(BadGateway()).create_live(request)
    failed = NarrativeService(FailingGateway()).create_live(request)
    assert rejected.draft is None and rejected.decision.action == "rejected"
    assert failed.draft is None and failed.decision.action == "unavailable"


def test_crewai_adapter_parses_structured_agent_outputs(sample, monkeypatch):
    crewai = pytest.importorskip("crewai")
    from match_intelligence.adapters.agents.crewai_gateway import (
        AnalysisProposal,
        CrewAIGateway,
        ObservedFacts,
        ReviewProposal,
        SelectionProposal,
    )

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "demo")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    outputs = [
        ObservedFacts(fact_indexes=[0], reason="Observed"),
        AnalysisProposal(angle="observed", reason="Supported"),
        SelectionProposal(fact_indexes=[0], angle="observed", reason="Relevant"),
        ReviewProposal(approved=True, reason="Grounded"),
    ]
    monkeypatch.setattr(
        crewai.Crew,
        "kickoff",
        lambda self: SimpleNamespace(
            tasks_output=[SimpleNamespace(pydantic=item) for item in outputs]
        ),
    )
    snapshot, candidates = sample
    plan = CrewAIGateway().plan(snapshot, candidates[0], ViewerPreferences())
    assert plan.fact_indexes == [0]
    assert plan.reviewer_approved
