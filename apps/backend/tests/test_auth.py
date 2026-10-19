"""Inicio de sesión con dos perfiles: aficionado y analista profesional."""

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.auth_router import get_auth_service
from match_intelligence.application.auth import (
    AuthError,
    AuthService,
    Role,
    StoredUser,
    User,
    hash_password,
)
from match_intelligence.main import app

SECRET = "s" * 40


def stored(username: str, role: Role, password: str) -> StoredUser:
    return StoredUser(User(username, username.title(), role), "salt-" + username, hash_password(password, "salt-" + username))


USERS = [stored("fan", Role.FAN, "fan-pass"), stored("pro", Role.ANALYST, "pro-pass")]


@pytest.fixture
def client() -> TestClient:
    auth = AuthService(USERS, SECRET)
    app.dependency_overrides[get_auth_service] = lambda: auth
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_login_returns_user_and_verifiable_token() -> None:
    service = AuthService(USERS, SECRET)
    issued, user = service.login("PRO ", "pro-pass")
    assert user.role is Role.ANALYST
    assert service.verify(issued) == user


@pytest.mark.parametrize(("username", "password"), [("pro", "wrong"), ("nobody", "pro-pass"), ("fan", "")])
def test_bad_credentials_are_rejected(username: str, password: str) -> None:
    with pytest.raises(AuthError):
        AuthService(USERS, SECRET).login(username, password)


def test_tampered_token_is_rejected() -> None:
    service = AuthService(USERS, SECRET)
    issued, _ = service.login("fan", "fan-pass")
    body, signature = issued.split(".")
    forged_body = body[:-2] + ("AA" if body[-2:] != "AA" else "BB")
    with pytest.raises(AuthError):
        service.verify(f"{forged_body}.{signature}")
    with pytest.raises(AuthError):
        AuthService(USERS, "x" * 40).verify(issued)


def test_expired_token_is_rejected() -> None:
    now = [1_000.0]
    service = AuthService(USERS, SECRET, clock=lambda: now[0])
    issued, _ = service.login("fan", "fan-pass")
    now[0] += 9 * 60 * 60
    with pytest.raises(AuthError):
        service.verify(issued)


def test_short_secret_is_refused() -> None:
    with pytest.raises(ValueError):
        AuthService(USERS, "short")


def test_documented_demo_accounts_work() -> None:
    """Las cuentas de docs/persona-4-api-y-frontend/README.md existen en demo-users.json."""
    from match_intelligence.adapters.http.auth_router import DEFAULT_USERS_FILE, _load_users

    service = AuthService(_load_users(DEFAULT_USERS_FILE), SECRET)
    assert service.login("aficionado", "aficionado-demo-2026")[1].role is Role.FAN
    assert service.login("analista", "analista-demo-2026")[1].role is Role.ANALYST


def test_login_and_me(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "fan", "password": "fan-pass"})
    headers = {"Authorization": f"Bearer {response.json()['token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json() == {"username": "fan", "display_name": "Fan", "role": "fan"}
    assert client.post("/api/v1/auth/login", json={"username": "fan", "password": "x"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
