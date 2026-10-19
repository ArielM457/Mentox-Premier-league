"""Consola del analista y revisión editorial protegida."""

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.auth_router import get_auth_service
from match_intelligence.adapters.http.registry import DEMO_MATCH_ID, _default_registry, get_registry
from match_intelligence.application.auth import AuthService, Role, StoredUser, User, hash_password
from match_intelligence.main import app

BASE = f"/api/v1/matches/{DEMO_MATCH_ID}"


def stored(username: str, role: Role, password: str) -> StoredUser:
    return StoredUser(User(username, username.title(), role), "salt-" + username, hash_password(password, "salt-" + username))


@pytest.fixture
def client() -> TestClient:
    registry = _default_registry()
    auth = AuthService([stored("fan", Role.FAN, "fan-pass"), stored("pro", Role.ANALYST, "pro-pass")], "s" * 40)
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_auth_service] = lambda: auth
    yield TestClient(app)
    app.dependency_overrides.clear()


def token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_analyst_feed_requires_analyst(client: TestClient) -> None:
    assert client.get(f"{BASE}/analyst/feed").status_code == 401
    assert client.get(f"{BASE}/analyst/feed", headers=token(client, "fan", "fan-pass")).status_code == 403


def test_analyst_feed_shows_everything_generated(client: TestClient) -> None:
    headers = token(client, "pro", "pro-pass")
    feed = client.get(f"{BASE}/analyst/feed", params={"until_video_ms": 42_000}, headers=headers).json()
    assert len(feed["events"]) == 10
    assert feed["snapshot"]["score"]["team-aurora"] == 1
    goal = next(m for m in feed["moments"] if m["candidate"]["kind"] == "goal")
    assert set(goal["drafts"]) == {"casual", "analyst"}
    assert goal["drafts"]["casual"]["explanation"] != goal["drafts"]["analyst"]["explanation"]
    assert goal["drafts"]["casual"]["source_event_ids"] == goal["drafts"]["analyst"]["source_event_ids"]
    assert set(goal["shown_in"]) == {"casual", "analyst"}
    pressure = next(m for m in feed["moments"] if m["candidate"]["kind"] == "pressure")
    assert pressure["shown_in"] == ["analyst"]
    assert pressure["candidate"]["evidence_limits"]
    assert any(c["suppressed"] or c["replaces_message_id"] for c in feed["commentary"])


def test_analyst_feed_never_reveals_future(client: TestClient) -> None:
    headers = token(client, "pro", "pro-pass")
    feed = client.get(f"{BASE}/analyst/feed", params={"until_video_ms": 20_000}, headers=headers).json()
    assert all(e["video_time_ms"] <= 20_000 for e in feed["events"])
    assert all(m["video_time_ms"] <= 20_000 for m in feed["moments"])
    assert not any(m["candidate"]["kind"] == "goal" for m in feed["moments"])


def test_only_analyst_can_review(client: TestClient) -> None:
    draft_id = client.get(f"{BASE}/summary").json()["draft"]["draft_id"]
    url = f"{BASE}/editorial/{draft_id}/review"
    body = {"decision": "approve", "reviewer": "Ana"}
    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers=token(client, "fan", "fan-pass")).status_code == 403
    assert client.post(url, json=body, headers=token(client, "pro", "pro-pass")).json()["status"] == "approved"
