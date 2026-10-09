"""Pruebas de la API de experiencia (Persona 4) con los adaptadores provisionales."""

import json

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.registry import (
    DEMO_MATCH_ID,
    _default_registry,
    get_registry,
)
from match_intelligence.application.match_session import schedule_overlays
from match_intelligence.main import app

BASE = f"/api/v1/matches/{DEMO_MATCH_ID}"


@pytest.fixture
def client() -> TestClient:
    registry = _default_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    yield TestClient(app)
    app.dependency_overrides.clear()


def overlays(client: TestClient, **params) -> list[dict]:
    response = client.get(f"{BASE}/overlays", params=params)
    assert response.status_code == 200, response.text
    return response.json()["overlays"]


def visible_at(messages: list[dict], video_time_ms: int) -> list[dict]:
    return [
        m for m in messages
        if not m["suppressed"] and m["video_time_ms"] <= video_time_ms < m["display_until_ms"]
    ]


def test_overlay_is_machine_readable(client: TestClient) -> None:
    """RF-19: identificador, tiempo, idioma, modo, texto, prioridad, duración y origen."""
    message = overlays(client)[0]
    for key in (
        "message_id", "draft_id", "clock_ms", "video_time_ms", "language", "mode",
        "headline", "priority", "show_for_ms", "source_event_ids", "display_until_ms",
    ):
        assert key in message
    assert message["contract_version"] == "1"
    assert message["source_event_ids"]


def test_overlay_time_comes_from_source_events(client: TestClient) -> None:
    events = client.get(f"{BASE}/events", params={"until_video_ms": 100_000}).json()["events"]
    video_by_id = {e["event_id"]: e["video_time_ms"] for e in events}
    for message in overlays(client):
        assert message["video_time_ms"] == max(video_by_id[eid] for eid in message["source_event_ids"])


def test_seek_rebuilds_same_screen_without_future_messages(client: TestClient) -> None:
    """RF-37: adelantar o pausar no muestra mensajes de otro momento."""
    full = overlays(client)
    for t in range(0, 42_000, 500):
        partial = overlays(client, until_video_ms=t)
        assert all(m["video_time_ms"] <= t for m in partial)
        assert [m["message_id"] for m in visible_at(partial, t)] == [
            m["message_id"] for m in visible_at(full, t)
        ]


def test_only_one_message_competes_for_screen(client: TestClient) -> None:
    """RNF-05: nunca hay dos mensajes visibles a la vez."""
    for params in ({}, {"mode": "analyst"}, {"mode": "player", "favorite_player_id": "aurora-8"}):
        messages = overlays(client, **params)
        for t in range(0, 42_000, 100):
            assert len(visible_at(messages, t)) <= 1


def test_scheduler_replaces_lower_priority_and_keeps_higher() -> None:
    from match_intelligence.domain.presentation import OverlayMessage

    def msg(mid: str, start: int, priority: int) -> OverlayMessage:
        return OverlayMessage(
            message_id=mid, draft_id=mid, candidate_id=None, match_id="m", period=1, clock_ms=start,
            video_time_ms=start, show_for_ms=5_000, priority=priority, kind="k", language="es",
            mode="casual", level="normal", headline=mid, explanation="", source_event_ids=[],
            display_until_ms=start + 5_000,
        )

    result = {m.message_id: m for m in schedule_overlays([msg("a", 0, 50), msg("b", 1_000, 90), msg("c", 2_000, 10)])}
    assert result["a"].display_until_ms == 1_000
    assert result["b"].replaces_message_id == "a"
    assert result["c"].suppressed


def test_casual_and_analyst_differ_but_share_sources(client: TestClient) -> None:
    """RF-23."""
    casual = {m["candidate_id"]: m for m in overlays(client, mode="casual")}
    analyst = {m["candidate_id"]: m for m in overlays(client, mode="analyst")}
    assert len(analyst) > len(casual)
    goal = "moment-evt-010"
    assert casual[goal]["explanation"] != analyst[goal]["explanation"]
    assert casual[goal]["source_event_ids"] == analyst[goal]["source_event_ids"]


def test_language_changes_text_not_facts(client: TestClient) -> None:
    """RF-22 y RF-27."""
    es = {m["candidate_id"]: m for m in overlays(client, language="es")}
    en = {m["candidate_id"]: m for m in overlays(client, language="en")}
    assert es.keys() == en.keys()
    for key in es:
        assert es[key]["headline"] != en[key]["headline"]
        assert es[key]["source_event_ids"] == en[key]["source_event_ids"]
        assert es[key]["language"] == "es" and en[key]["language"] == "en"
    assert "M. Luz" in es["moment-evt-010"]["headline"] and "M. Luz" in en["moment-evt-010"]["headline"]


def test_levels_change_detail_not_facts(client: TestClient) -> None:
    """RF-36."""
    by_level = {
        level: {m["candidate_id"]: m for m in overlays(client, level=level)}
        for level in ("simple", "normal", "advanced")
    }
    goal = "moment-evt-010"
    lengths = [len(by_level[level][goal]["explanation"]) for level in ("simple", "normal", "advanced")]
    assert lengths == sorted(lengths) and len(set(lengths)) == 3
    assert len({tuple(by_level[level][goal]["source_event_ids"]) for level in by_level}) == 1


@pytest.mark.parametrize("team", ["team-aurora", "team-rio"])
def test_favorite_team_never_hides_rival_goal(client: TestClient, team: str) -> None:
    """RF-24: se prioriza al club sin ocultar hechos decisivos del rival."""
    messages = overlays(client, favorite_team_id=team)
    assert any(m["kind"] == "goal" for m in messages)
    neutral = {m["candidate_id"]: m["priority"] for m in overlays(client)}
    for m in messages:
        events = client.get(f"{BASE}/drafts/{m['draft_id']}/sources").json()["events"]
        if m["candidate_id"] in neutral and events[-1]["team_id"] == team and m["kind"] != "goal":
            assert m["priority"] > neutral[m["candidate_id"]]


def test_favorite_player_raises_priority_only_when_involved(client: TestClient) -> None:
    """RF-25: un jugador que interviene y otro que no."""
    neutral = {m["candidate_id"]: m["priority"] for m in overlays(client, mode="analyst")}
    involved = {m["candidate_id"]: m["priority"] for m in overlays(client, mode="analyst", favorite_player_id="aurora-8")}
    not_involved = {m["candidate_id"]: m["priority"] for m in overlays(client, mode="analyst", favorite_player_id="rio-8")}
    assert involved["moment-evt-006"] > neutral["moment-evt-006"]
    assert not_involved == neutral


def test_player_mode_reports_quiet_stretches(client: TestClient) -> None:
    """RF-26."""
    messages = overlays(client, mode="player", favorite_player_id="rio-10")
    quiet = [m for m in messages if m["kind"] == "player_quiet"]
    assert quiet and all("P. Cauce" in m["headline"] for m in quiet)
    assert {m["kind"] for m in messages} <= {"pressure", "goal", "player_quiet"}


def test_player_mode_requires_player(client: TestClient) -> None:
    response = client.get(f"{BASE}/overlays", params={"mode": "player"})
    assert response.status_code == 400


def test_unknown_preferences_and_match_are_rejected(client: TestClient) -> None:
    assert client.get(f"{BASE}/overlays", params={"favorite_team_id": "x"}).status_code == 400
    assert client.get("/api/v1/matches/none/state", params={"video_time_ms": 0}).status_code == 404


def test_events_and_state_never_reveal_future(client: TestClient) -> None:
    events = client.get(f"{BASE}/events", params={"until_video_ms": 20_000}).json()["events"]
    assert events and all(e["video_time_ms"] <= 20_000 for e in events)
    before = client.get(f"{BASE}/state", params={"video_time_ms": 33_000}).json()
    after = client.get(f"{BASE}/state", params={"video_time_ms": 34_000}).json()
    assert before["score"]["team-aurora"] == 0 and after["score"]["team-aurora"] == 1


def test_sources_explain_a_message(client: TestClient) -> None:
    message = overlays(client)[-1]
    body = client.get(f"{BASE}/drafts/{message['draft_id']}/sources").json()
    assert [e["event_id"] for e in body["events"]] == message["source_event_ids"]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("¿Cuántos pases lleva Aurora?", "Aurora FC: 4"),
        ("¿Cuántos tiros tiene M. Luz?", "M. Luz: 1"),
        ("¿Cuántos tiros tiene P. Cauce?", "P. Cauce: 0"),
        ("Compara las recuperaciones por tramo", "primer tramo"),
    ],
)
def test_questions_use_available_events(client: TestClient, question: str, expected: str) -> None:
    """RF-34."""
    body = client.post(f"{BASE}/questions", json={"question": question, "video_time_ms": 40_000}).json()
    assert expected in body["answer"]["headline"]


def test_question_without_data_is_acknowledged(client: TestClient) -> None:
    body = client.post(f"{BASE}/questions", json={"question": "¿Qué tiempo hace?", "video_time_ms": 40_000}).json()
    assert body["answer"]["source_event_ids"] == []
    assert "No puedo" in body["answer"]["headline"]


def test_question_does_not_count_future_events(client: TestClient) -> None:
    body = client.post(f"{BASE}/questions", json={"question": "goles", "video_time_ms": 10_000}).json()
    assert "Aurora FC 0" in body["answer"]["headline"]


def test_final_summary_is_held_until_approved(client: TestClient) -> None:
    """RF-38."""
    summary = client.get(f"{BASE}/summary").json()
    draft_id = summary["draft"]["draft_id"]
    assert summary["status"] == "pending"
    assert client.get(f"{BASE}/editorial/{draft_id}/published").status_code == 409

    approved = client.post(f"{BASE}/editorial/{draft_id}/review", json={"decision": "approve", "reviewer": "Ana"})
    assert approved.json()["status"] == "approved"
    published = client.get(f"{BASE}/editorial/{draft_id}/published")
    assert published.status_code == 200 and published.json()["editorial_status"] == "approved"
    again = client.post(f"{BASE}/editorial/{draft_id}/review", json={"decision": "reject", "reviewer": "Ana"})
    assert again.status_code == 409


def test_rejected_summary_is_not_published(client: TestClient) -> None:
    draft_id = client.get(f"{BASE}/summary", params={"language": "en"}).json()["draft"]["draft_id"]
    client.post(f"{BASE}/editorial/{draft_id}/review", json={"decision": "reject", "reviewer": "Ana", "note": "Falta contexto"})
    assert client.get(f"{BASE}/editorial/{draft_id}/published").status_code == 409


def test_summary_focus_keeps_facts(client: TestClient) -> None:
    """RF-35."""
    plain = client.get(f"{BASE}/summary").json()["draft"]
    focused = client.get(f"{BASE}/summary", params={"favorite_player_id": "aurora-9"}).json()["draft"]
    assert plain["draft_id"] != focused["draft_id"]
    assert focused["explanation"].startswith(plain["explanation"].rstrip("."))
    assert "Enfoque en M. Luz" in focused["explanation"]


def test_valid_report_withdraws_and_corrects(client: TestClient) -> None:
    """RF-39: reporte válido."""
    client.post("/api/v1/matches", json={"match_id": "faulty", "inject_error_in": "goal"})
    goal = next(m for m in client.get("/api/v1/matches/faulty/overlays").json()["overlays"] if m["kind"] == "goal")
    assert "M. Luz" not in goal["headline"]

    report = client.post(
        "/api/v1/matches/faulty/reports",
        json={"draft_id": goal["draft_id"], "message_id": goal["message_id"], "reason": "El goleador es otro"},
    ).json()
    assert report["outcome"] == "withdrawn" and report["issues"]
    assert "M. Luz" in report["corrected_draft"]["headline"]

    fixed = next(m for m in client.get("/api/v1/matches/faulty/overlays").json()["overlays"] if m["kind"] == "goal")
    assert fixed["corrected"] and "M. Luz" in fixed["headline"]
    assert len(client.get("/api/v1/matches/faulty/reports").json()) == 1


def test_invalid_report_is_confirmed(client: TestClient) -> None:
    """RF-39: reporte que no corresponde."""
    goal = next(m for m in overlays(client) if m["kind"] == "goal")
    report = client.post(f"{BASE}/reports", json={"draft_id": goal["draft_id"], "reason": "No fue gol"}).json()
    assert report["outcome"] == "confirmed" and report["corrected_draft"] is None


def test_playback_controls_use_video_sync(client: TestClient) -> None:
    assert client.post(f"{BASE}/playback", json={"action": "play", "video_time_ms": 20_000}).json()["events_applied"] == 5
    paused = client.post(f"{BASE}/playback", json={"action": "pause", "video_time_ms": 10_000}).json()
    assert paused["state"] == "paused" and paused["events_applied"] == 2
    restarted = client.post(f"{BASE}/playback", json={"action": "restart"}).json()
    assert restarted["video_time_ms"] == 0 and restarted["events_applied"] == 0
    assert client.post(f"{BASE}/playback", json={"action": "seek"}).status_code == 400


def test_live_stream_sends_new_messages_with_timing(client: TestClient) -> None:
    """Canal en directo: solo mensajes posteriores al punto de partida y con marca de envío."""
    names: list[str] = []
    payloads: list[dict] = []
    with client.stream("GET", f"{BASE}/stream", params={"from_video_ms": 30_000, "speed": 8}) as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        event = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                event = line[7:]
                names.append(event)
            elif line.startswith("data: ") and event == "overlay":
                payloads.append(json.loads(line[6:]))
            if event == "end":
                break
    assert names[0] == "ready" and names[-1] == "end"
    assert payloads and all(p["overlay"]["video_time_ms"] > 30_000 for p in payloads)
    assert all("emitted_at_ms" in p and "pipeline_ms" in p for p in payloads)
