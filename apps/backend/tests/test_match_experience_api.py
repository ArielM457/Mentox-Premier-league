"""Pruebas de la API de experiencia (Persona 4) con los adaptadores provisionales."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.registry import (
    DEMO_MATCH_ID,
    LIVE_MATCH_ID,
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
    for params in ({}, {"mode": "analyst"}, {"mode": "professional_analyst"}, {"mode": "player", "favorite_player_id": "aurora-8"}):
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


def test_professional_analyst_returns_advanced_overlays(client: TestClient) -> None:
    messages = overlays(client, mode="professional_analyst", level="simple")

    assert messages
    assert all(message["mode"] == "professional_analyst" for message in messages)
    assert all(message["level"] == "advanced" for message in messages)


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


def test_portuguese_player_mode_advanced_returns_overlays(client: TestClient) -> None:
    response = client.get(
        f"{BASE}/overlays",
        params={
            "language": "pt",
            "mode": "player",
            "level": "advanced",
            "favorite_team_id": "team-rio",
            "favorite_player_id": "rio-8",
            "until_video_ms": 173_000,
        },
    )

    assert response.status_code == 200, response.text
    items = response.json()["overlays"]
    assert items
    assert all(item["language"] == "pt" for item in items)
    portuguese_terms = ("recupera", "progressão", "pressão", "passe", "finalização", "gol")
    assert any(
        term in item["explanation"].casefold()
        for item in items
        for term in portuguese_terms
    )


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


def test_live_comments_use_friendly_text_and_keep_evidence_separate(
    client: TestClient,
) -> None:
    """La pantalla no expone claves internas, pero la evidencia sigue disponible."""
    response = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/overlays",
        params={"mode": "analyst", "level": "advanced"},
    )
    assert response.status_code == 200
    shot = next(
        message
        for message in response.json()["overlays"]
        if message["candidate_id"] == "moment-live-032"
    )

    assert shot["explanation"] == "Río Unido genera una ocasión clara."
    assert not shot["explanation"].startswith("[")
    assert all(
        marker not in shot["explanation"]
        for marker in ("Datos:", "Eventos:", "shot=", "live-032")
    )
    assert shot["source_event_ids"] == ["live-032"]

    sources = client.get(
        f"/api/v1/matches/{LIVE_MATCH_ID}/drafts/{shot['draft_id']}/sources"
    )
    assert sources.status_code == 200
    assert [event["event_id"] for event in sources.json()["events"]] == ["live-032"]

    progressive = next(
        message
        for message in response.json()["overlays"]
        if message["candidate_id"] == "moment-live-003"
    )
    assert progressive["explanation"] == "Aurora FC rompe una línea y hace avanzar la jugada."
    for message in response.json()["overlays"]:
        assert all(
            marker not in message["explanation"]
            for marker in (
                "Datos:", "Eventos:", "forward_progress", "pitch_percent",
                "coordenadas de campo", "no en metros", "live-",
            )
        )


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


def test_summary_variants_select_the_expected_events(client: TestClient) -> None:
    short = client.get(f"{BASE}/summary", params={"summary_type": "short"}).json()["draft"]
    extended = client.get(f"{BASE}/summary", params={"summary_type": "extended"}).json()["draft"]
    player = client.get(
        f"{BASE}/summary",
        params={"summary_type": "player_danger", "player_id": "aurora-9"},
    ).json()["draft"]

    assert short["draft_id"] != extended["draft_id"] != player["draft_id"]
    assert "tiros" not in short["explanation"]
    assert "tiros" in extended["explanation"]
    assert "Peligro de M. Luz" in player["explanation"]
    assert set(short["source_event_ids"]) < set(extended["source_event_ids"])


def test_player_summary_requires_a_player_from_the_match(client: TestClient) -> None:
    missing = client.get(f"{BASE}/summary", params={"summary_type": "player_danger"})
    unknown = client.get(
        f"{BASE}/summary",
        params={"summary_type": "player_danger", "player_id": "unknown"},
    )

    assert missing.status_code == 400
    assert unknown.status_code == 400


def test_summary_ignores_identifiers_outside_the_roster(client: TestClient) -> None:
    plain = client.get(f"{BASE}/summary").json()["draft"]
    stray_player = client.get(f"{BASE}/summary", params={"player_id": "anything"}).json()["draft"]
    stray_favorite = client.get(f"{BASE}/summary", params={"favorite_player_id": "anything"}).json()["draft"]

    assert stray_player["draft_id"] == stray_favorite["draft_id"] == plain["draft_id"]
    assert "anything" not in stray_favorite["explanation"]
    assert len(client.get(f"{BASE}/editorial").json()) == 1


def test_new_summary_languages_are_accepted_and_translated(client: TestClient) -> None:
    expected = {"de": "Zusammenfassung", "zh": "比赛摘要", "hi": "मैच सारांश", "fr": "Résumé", "pt": "Resumo"}
    for language, title in expected.items():
        response = client.get(
            f"{BASE}/summary",
            params={"summary_type": "short", "language": language},
        )
        assert response.status_code == 200
        assert response.json()["draft"]["headline"].startswith(title)


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


EXAMPLES = Path(__file__).resolve().parents[3] / "docs" / "persona-4-api-y-frontend" / "ejemplos"


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("overlay-message-v1.valido.json", True),
        ("overlay-message-v1.sin-opcionales.json", True),
        ("overlay-message-v1.invalido.json", False),
    ],
)
def test_overlay_contract_examples(name: str, valid: bool) -> None:
    """Ejemplos compartidos del contrato: válido, sin opcionales e inválido."""
    from pydantic import ValidationError

    from match_intelligence.domain.presentation import OverlayMessage

    data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    if valid:
        OverlayMessage.model_validate(data)
    else:
        with pytest.raises(ValidationError):
            OverlayMessage.model_validate(data)


def test_two_half_scenario_from_persona_2_is_playable(client: TestClient) -> None:
    """El escenario largo de Persona 2 se carga y se reproduce con la misma API."""
    base = "/api/v1/matches/synthetic-analytics-001"
    detail = client.get(base).json()
    assert detail["event_count"] == 178 and detail["duration_ms"] > 600_000
    assert client.get(f"{base}/state", params={"video_time_ms": detail["duration_ms"]}).json()["score"] == {
        "team-aurora": 1,
        "team-rio": 1,
    }
    messages = client.get(f"{base}/overlays").json()["overlays"]
    assert sum(m["kind"] == "goal" for m in messages) == 2
    for t in range(0, detail["duration_ms"], 1_000):
        assert len(visible_at(messages, t)) <= 1


def test_unknown_scenario_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/matches", json={"scenario": "real-premier-league"})
    assert response.status_code == 422


def test_catalog_exposes_recent_upcoming_and_optional_live_matches(client: TestClient) -> None:
    matches = client.get("/api/v1/matches").json()
    by_id = {match["match_id"]: match for match in matches}
    assert by_id["synthetic-acceptance-001"]["status"] == "FT"
    assert by_id["synthetic-analytics-001"]["status"] == "UPCOMING"
    assert by_id[LIVE_MATCH_ID]["status"] == "LIVE"
    assert all(match["status"] in {"LIVE", "UPCOMING", "FT"} for match in matches)


def test_prematch_agent_returns_ui_data_for_both_teams(client: TestClient) -> None:
    response = client.get("/api/v1/matches/synthetic-analytics-001/preview")
    assert response.status_code == 200
    preview = response.json()
    assert preview["generated_by"] == "prematch-tactics-agent"
    assert preview["status"] == "UPCOMING"
    assert len(preview["home"]["formations"]) >= 2
    assert len(preview["away"]["formations"]) >= 2
    assert len(preview["simulations"]) == 10
    assert {simulation["team_id"] for simulation in preview["simulations"]} == {
        preview["home"]["team_id"], preview["away"]["team_id"]
    }
    for team in (preview["home"], preview["away"]):
        for formation in team["formations"]:
            assert len(formation["players"]) == 11
            assert all(player["team_id"] == team["team_id"] for player in formation["players"])
            assert all(0 <= player["position"][axis] <= 100 for player in formation["players"] for axis in ("x", "y"))
    for simulation in preview["simulations"]:
        attacking_team = (
            preview["home"] if simulation["team_id"] == preview["home"]["team_id"] else preview["away"]
        )
        attacking_ids = [player["player_id"] for player in attacking_team["formations"][0]["players"]]
        attacks_right = simulation["team_id"] == preview["home"]["team_id"]

        def attacking_x(position: dict) -> float:
            return position["x"] if attacks_right else 100 - position["x"]

        assert simulation["frames"][-1]["phase"] == "Gol simulado"
        assert len(simulation["frames"]) == 13
        assert [frame["at_ms"] for frame in simulation["frames"]] == sorted(
            frame["at_ms"] for frame in simulation["frames"]
        )
        assert all(
            current["at_ms"] - previous["at_ms"] <= 1_000
            for previous, current in zip(simulation["frames"], simulation["frames"][1:], strict=False)
        )
        assert all(frame["action"] for frame in simulation["frames"])
        assert all(len(frame["players"]) == 22 for frame in simulation["frames"])
        assert all(len({player["player_id"] for player in frame["players"]}) == 22 for frame in simulation["frames"])
        for frame in simulation["frames"]:
            involved = set(frame["involved_player_ids"])
            assert 2 <= len(involved) < 22
            assert involved <= {player["player_id"] for player in frame["players"]}
            assert {
                player["team_id"] for player in frame["players"]
                if player["player_id"] in involved
            } == {preview["home"]["team_id"], preview["away"]["team_id"]}
        assert simulation["frames"][-1]["ball_owner_id"] is None
        assert simulation["frames"][-1]["ball"]["x"] <= 3 or simulation["frames"][-1]["ball"]["x"] >= 97
        assert len(simulation["frames"][:-1]) >= 10
        assert len({frame["ball_owner_id"] for frame in simulation["frames"][:-1]}) >= 5
        for frame in simulation["frames"][:-1]:
            owner = next(
                player for player in frame["players"]
                if player["player_id"] == frame["ball_owner_id"]
            )
            assert owner["position"] == frame["ball"]
        assert all(
            {player["team_id"] for player in frame["players"]}
            == {preview["home"]["team_id"], preview["away"]["team_id"]}
            for frame in simulation["frames"]
        )
        assert len({(frame["ball"]["x"], frame["ball"]["y"]) for frame in simulation["frames"]}) > 4
        defending_team_id = (
            preview["away"]["team_id"]
            if simulation["team_id"] == preview["home"]["team_id"]
            else preview["home"]["team_id"]
        )
        for previous, current in zip(
            simulation["frames"], simulation["frames"][1:], strict=False
        ):
            previous_by_id = {
                player["player_id"]: player for player in previous["players"]
            }
            moving_defenders = [
                player
                for player in current["players"]
                if player["team_id"] == defending_team_id
                and (
                    abs(
                        player["position"]["x"]
                        - previous_by_id[player["player_id"]]["position"]["x"]
                    ) > 0.05
                    or abs(
                        player["position"]["y"]
                        - previous_by_id[player["player_id"]]["position"]["y"]
                    ) > 0.05
                )
            ]
            assert len(moving_defenders) >= 9
            moving_attackers = [
                player
                for player in current["players"]
                if player["team_id"] == simulation["team_id"]
                and (
                    abs(
                        player["position"]["x"]
                        - previous_by_id[player["player_id"]]["position"]["x"]
                    ) > 0.05
                    or abs(
                        player["position"]["y"]
                        - previous_by_id[player["player_id"]]["position"]["y"]
                    ) > 0.05
                )
            ]
            assert len(moving_attackers) >= 9
        positions_by_player = {
            player["player_id"]: {
                (frame_player["position"]["x"], frame_player["position"]["y"])
                for frame in simulation["frames"]
                for frame_player in frame["players"]
                if frame_player["player_id"] == player["player_id"]
            }
            for player in simulation["frames"][0]["players"]
        }
        assert all(len(positions) > 1 for positions in positions_by_player.values())

        # La estructura conserva las funciones: portero en inicio y defensores
        # como cobertura, incluso cuando el equipo presiona en campo rival.
        for frame in simulation["frames"]:
            by_id = {player["player_id"]: player for player in frame["players"]}
            assert attacking_x(by_id[attacking_ids[0]]["position"]) <= 25
            assert all(
                attacking_x(by_id[player_id]["position"]) <= 55
                for player_id in attacking_ids[1:3]
            )

        # Después de pasar, el jugador continúa desde donde estaba y no vuelve
        # de golpe a la coordenada original de la formación.
        for previous, current in zip(simulation["frames"], simulation["frames"][1:], strict=False):
            previous_owner = previous["ball_owner_id"]
            current_owner = current["ball_owner_id"]
            if current_owner is not None and current_owner != previous_owner:
                prepared_receiver = next(
                    p for p in previous["players"] if p["player_id"] == current_owner
                )
                assert abs(prepared_receiver["position"]["x"] - current["ball"]["x"]) <= 12
                assert abs(prepared_receiver["position"]["y"] - current["ball"]["y"]) <= 12
            if previous_owner is None or previous_owner == current["ball_owner_id"]:
                continue
            previous_player = next(p for p in previous["players"] if p["player_id"] == previous_owner)
            current_player = next(p for p in current["players"] if p["player_id"] == previous_owner)
            assert abs(current_player["position"]["x"] - previous_player["position"]["x"]) <= 12
            assert abs(current_player["position"]["y"] - previous_player["position"]["y"]) <= 12

    information = preview["information"]
    assert information["source"] == {
        "document_id": "prematch-synthetic-analytics-001-v1",
        "storage_kind": "local_fixture",
        "approved": True,
        "synthetic": True,
        "updated_at": "2026-10-23",
    }
    assert len(information["teams"]) == 2
    assert all(len(team["recent_results"]) == 5 for team in information["teams"])
    assert all(team["availability"] for team in information["teams"])


def test_prematch_includes_full_field_counterattacks_and_forward_progression(
    client: TestClient,
) -> None:
    preview = client.get(f"/api/v1/matches/{LIVE_MATCH_ID}/preview").json()
    expected_keys = {"full_field_counter", "vertical_progression"}

    for team in (preview["home"], preview["away"]):
        simulations = {
            simulation["simulation_id"].removeprefix(f'{team["team_id"]}-'): simulation
            for simulation in preview["simulations"]
            if simulation["team_id"] == team["team_id"]
        }
        assert expected_keys <= simulations.keys()
        attacks_right = team["team_id"] == preview["home"]["team_id"]
        defending_team_id = (
            preview["away"]["team_id"]
            if attacks_right
            else preview["home"]["team_id"]
        )

        for tactic_key in expected_keys:
            simulation = simulations[tactic_key]
            progress = [
                frame["ball"]["x"] if attacks_right else 100 - frame["ball"]["x"]
                for frame in simulation["frames"]
            ]
            assert progress[0] <= 25
            assert progress[-1] >= 97
            assert sum(current > previous for previous, current in zip(progress, progress[1:])) >= 10

            for frame in simulation["frames"]:
                outfield_x = [
                    player["position"]["x"]
                    if attacks_right
                    else 100 - player["position"]["x"]
                    for player in frame["players"]
                    if player["shirt_number"] != 1
                ]
                assert min(outfield_x) <= 40
                assert max(outfield_x) >= 70

                closest_pressure = min(
                    (
                        (player["position"]["x"] - frame["ball"]["x"]) ** 2
                        + (player["position"]["y"] - frame["ball"]["y"]) ** 2
                    ) ** 0.5
                    for player in frame["players"]
                    if player["team_id"] == defending_team_id
                    and player["shirt_number"] != 1
                )
                assert closest_pressure <= 12


def test_prematch_includes_a_striker_shot_from_outside_the_box(
    client: TestClient,
) -> None:
    preview = client.get(f"/api/v1/matches/{LIVE_MATCH_ID}/preview").json()

    for team in (preview["home"], preview["away"]):
        simulation = next(
            item
            for item in preview["simulations"]
            if item["simulation_id"] == f'{team["team_id"]}-outside_box_shot'
        )
        attacks_right = team["team_id"] == preview["home"]["team_id"]
        shot = next(frame for frame in simulation["frames"] if frame["phase"] == "Remate lejano")
        shot_x = shot["ball"]["x"] if attacks_right else 100 - shot["ball"]["x"]
        forwards = {
            player["player_id"] for player in team["formations"][0]["players"][-3:]
        }

        assert simulation["title"] == "Remate desde fuera del área"
        assert 75 <= shot_x <= 83
        assert shot["ball_owner_id"] in forwards
        assert simulation["frames"][-1]["ball_owner_id"] is None


def test_live_match_has_enough_players_and_touches_for_coordinated_tactics(client: TestClient) -> None:
    response = client.get(f"/api/v1/matches/{LIVE_MATCH_ID}/preview")
    assert response.status_code == 200
    preview = response.json()
    assert len(preview["home"]["formations"][0]["players"]) == 11
    assert len(preview["away"]["formations"][0]["players"]) == 11
    for simulation in preview["simulations"]:
        contact_frames = [frame for frame in simulation["frames"] if frame["ball_owner_id"]]
        assert len(contact_frames) >= 10
        assert len({frame["ball_owner_id"] for frame in contact_frames}) >= 5
        for frame in contact_frames:
            owner = next(
                player for player in frame["players"]
                if player["player_id"] == frame["ball_owner_id"]
            )
            assert owner["position"] == frame["ball"]
