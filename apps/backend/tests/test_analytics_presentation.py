"""La analítica real de Persona 2 detrás de la API de Persona 4."""

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http import registry as registry_module
from match_intelligence.adapters.http.registry import (
    ANALYTICS_MATCH_ID,
    DEMO_MATCH_ID,
    MatchRegistry,
    _default_registry,
    get_registry,
)
from match_intelligence.adapters.provisional.narrative import ProvisionalNarrative
from match_intelligence.adapters.sources.analytics_scenarios import generate_analytics_scenario
from match_intelligence.application.analytics.pipeline import MatchAnalytics
from match_intelligence.application.analytics.presentation import PresentationAnalytics
from match_intelligence.domain import presentation
from match_intelligence.main import app


def persona2_registry() -> MatchRegistry:
    registry = MatchRegistry(
        analytics=PresentationAnalytics,
        narrative=lambda inject: ProvisionalNarrative(inject_error_in=inject),
    )
    registry.load_synthetic()
    registry.load_synthetic(scenario="analytics", match_id=ANALYTICS_MATCH_ID)
    return registry


@pytest.fixture
def client() -> TestClient:
    registry = persona2_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_adapter_returns_presentation_contracts_with_the_same_facts() -> None:
    match = generate_analytics_scenario()
    adapter = PresentationAnalytics()
    events = [e for e in match.events if e.video_time_ms <= 300_000]

    snapshot = adapter.snapshot(match.metadata, events, video_time_ms=300_000)
    full = MatchAnalytics().snapshot(match.metadata, events, video_time_ms=300_000)
    assert isinstance(snapshot, presentation.MatchSnapshot)
    assert snapshot.score == full.score and snapshot.clock_ms == full.clock_ms
    assert [(m.key, m.team_id, m.player_id, m.value) for m in snapshot.metrics] == [
        (m.key, m.team_id, m.player_id, m.value) for m in full.metrics
    ]

    preferences = presentation.ViewerPreferences(mode=presentation.ViewerMode.ANALYST)
    candidates = adapter.candidates(match.metadata, match.events, preferences)
    expected = MatchAnalytics().candidates(match.metadata, match.events, preferences)
    assert all(isinstance(c, presentation.InsightCandidate) for c in candidates)
    assert [(c.candidate_id, c.priority, c.source_event_ids) for c in candidates] == [
        (c.candidate_id, c.priority, c.source_event_ids) for c in expected
    ]


@pytest.mark.parametrize("match_id", [DEMO_MATCH_ID, ANALYTICS_MATCH_ID])
def test_api_routes_work_with_the_real_engine(client: TestClient, match_id: str) -> None:
    base = f"/api/v1/matches/{match_id}"
    state = client.get(f"{base}/state", params={"video_time_ms": 40_000})
    assert state.status_code == 200, state.text
    keys = {m["key"] for m in state.json()["metrics"]}
    assert {"goals", "shots", "passes_attempted", "pass_accuracy", "recoveries", "pressures"} <= keys
    assert "control_index" in keys

    overlays = client.get(f"{base}/overlays", params={"mode": "analyst"})
    assert overlays.status_code == 200, overlays.text
    messages = overlays.json()["overlays"]
    assert messages and all(m["headline"] != m["kind"] for m in messages)

    answer = client.post(f"{base}/questions", json={"question": "¿Cuántos tiros lleva Aurora?", "video_time_ms": 40_000})
    assert answer.status_code == 200, answer.text


def test_favorite_player_raises_priority_only_when_involved(client: TestClient) -> None:
    """RF-25 con los momentos de Persona 2."""
    base = f"/api/v1/matches/{ANALYTICS_MATCH_ID}/overlays"

    def priorities(**params: str) -> dict[str, int]:
        messages = client.get(base, params={"mode": "analyst", **params}).json()["overlays"]
        return {m["candidate_id"]: m["priority"] for m in messages}

    match = generate_analytics_scenario()
    involved = MatchAnalytics().candidates(match.metadata, match.events, {"mode": "analyst"})
    player = next(c.player_ids[0] for c in involved if c.player_ids and c.kind == "shot")
    neutral = priorities()
    favorite = priorities(favorite_player_id=player)
    raised = [cid for cid in neutral if cid in favorite and favorite[cid] > neutral[cid]]
    assert raised
    for candidate in involved:
        if candidate.candidate_id in raised:
            assert player in candidate.player_ids


@pytest.mark.parametrize("language", ["es", "en"])
def test_provisional_narrative_names_every_persona_2_moment(language: str) -> None:
    match = generate_analytics_scenario()
    preferences = presentation.ViewerPreferences(
        language=presentation.Language(language), mode=presentation.ViewerMode.ANALYST
    )
    narrative = ProvisionalNarrative()
    analytics = PresentationAnalytics()
    candidates = analytics.candidates(match.metadata, match.events, preferences)
    assert {c.kind for c in candidates} >= {"control_shift", "chaos_phase", "player_milestone"}
    for candidate in candidates:
        moment_ms = max(e.video_time_ms for e in match.events if e.event_id in candidate.source_event_ids)
        events = [e for e in match.events if e.video_time_ms <= moment_ms]
        snapshot = analytics.snapshot(match.metadata, events, video_time_ms=moment_ms)
        draft = narrative.live(match.metadata, snapshot, candidate, preferences)
        assert draft.headline != candidate.kind
        assert "?" not in draft.headline


def test_default_registry_reads_the_engine_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTICS_ENGINE", "persona2")
    monkeypatch.delenv("MATCH_SOURCE", raising=False)
    registry = _default_registry()
    session = registry.get(ANALYTICS_MATCH_ID)
    assert isinstance(session.analytics, PresentationAnalytics)
    assert session.snapshot(60_000).match_id == ANALYTICS_MATCH_ID


def test_default_registry_keeps_the_provisional_engine_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANALYTICS_ENGINE", raising=False)
    monkeypatch.delenv("MATCH_SOURCE", raising=False)
    from match_intelligence.adapters.provisional.analytics import ProvisionalAnalytics

    assert isinstance(_default_registry().get(DEMO_MATCH_ID).analytics, ProvisionalAnalytics)


@pytest.mark.parametrize(
    ("name", "value"),
    [("ANALYTICS_ENGINE", "magic"), ("MATCH_SOURCE", "excel")],
)
def test_unknown_settings_fail_with_a_clear_message(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match=name):
        _default_registry()


def test_supabase_source_requires_its_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATCH_SOURCE", "supabase")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
        registry_module._default_registry()


def test_unreachable_supabase_falls_back_to_synthetic_matches(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Una cadena que Azure no alcanza no debe dejar la API sin partidos."""
    from match_intelligence.adapters.storage import supabase_store

    class Unreachable:
        def load_matches(self):
            raise OSError('connection to server at "2600:1f18::1", port 5432 failed')

    monkeypatch.setenv("MATCH_SOURCE", "supabase")
    monkeypatch.setenv("ANALYTICS_ENGINE", "persona2")
    monkeypatch.setattr(supabase_store.SupabaseMatchStore, "from_env", classmethod(lambda cls: Unreachable()))
    with caplog.at_level("WARNING"):
        registry = _default_registry()
    assert sorted(s.match_id for s in registry.all()) == sorted(
        [DEMO_MATCH_ID, ANALYTICS_MATCH_ID, "synthetic-live-001"]
    )
    assert "No se pudo leer Supabase" in caplog.text and "OSError" in caplog.text
