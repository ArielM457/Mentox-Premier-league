"""Inicio de sesión con dos perfiles: aficionado y analista profesional."""

import pytest
from fastapi.testclient import TestClient

from match_intelligence.adapters.http.auth_router import get_auth_service
from match_intelligence.application.auth import (
    LOCKOUT_S,
    MAX_FAILED_ATTEMPTS,
    TOKEN_TTL_S,
    AuthError,
    AuthService,
    LockedError,
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


class Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def client() -> TestClient:
    auth = AuthService(USERS, SECRET)
    app.dependency_overrides[get_auth_service] = lambda: auth
    yield TestClient(app)
    app.dependency_overrides.clear()


# ----- servicio -------------------------------------------------------------

def test_login_returns_session_with_expiry() -> None:
    clock = Clock()
    service = AuthService(USERS, SECRET, clock=clock)
    session = service.login("PRO ", "pro-pass")
    assert session.user.role is Role.ANALYST
    assert session.expires_at == int(clock.now) + TOKEN_TTL_S
    assert service.verify(session.token) == session.user


def test_each_login_gets_its_own_token() -> None:
    service = AuthService(USERS, SECRET)
    assert service.login("fan", "fan-pass").token != service.login("fan", "fan-pass").token


@pytest.mark.parametrize(("username", "password"), [("pro", "wrong"), ("nobody", "pro-pass"), ("fan", "")])
def test_bad_credentials_are_rejected(username: str, password: str) -> None:
    with pytest.raises(AuthError):
        AuthService(USERS, SECRET).login(username, password)


def test_failed_attempts_count_down_then_lock() -> None:
    clock = Clock()
    service = AuthService(USERS, SECRET, clock=clock)
    for expected_left in range(MAX_FAILED_ATTEMPTS - 1, 0, -1):
        with pytest.raises(AuthError) as error:
            service.login("pro", "wrong")
        assert error.value.attempts_left == expected_left
    with pytest.raises(LockedError):
        service.login("pro", "wrong")
    # Bloqueada incluso con la contraseña correcta.
    with pytest.raises(LockedError) as locked:
        service.login("pro", "pro-pass")
    assert 0 < locked.value.retry_after_s <= LOCKOUT_S
    clock.now += LOCKOUT_S + 1
    assert service.login("pro", "pro-pass").user.username == "pro"


def test_successful_login_resets_failures() -> None:
    service = AuthService(USERS, SECRET)
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        with pytest.raises(AuthError):
            service.login("fan", "wrong")
    service.login("fan", "fan-pass")
    with pytest.raises(AuthError) as error:
        service.login("fan", "wrong")
    assert error.value.attempts_left == MAX_FAILED_ATTEMPTS - 1


def test_lockout_is_per_account() -> None:
    service = AuthService(USERS, SECRET)
    for _ in range(MAX_FAILED_ATTEMPTS):
        with pytest.raises(AuthError):
            service.login("pro", "wrong")
    assert service.login("fan", "fan-pass").user.username == "fan"


def test_logout_revokes_token() -> None:
    service = AuthService(USERS, SECRET)
    session = service.login("fan", "fan-pass")
    service.logout(session.token)
    with pytest.raises(AuthError):
        service.verify(session.token)


def test_tampered_token_is_rejected() -> None:
    service = AuthService(USERS, SECRET)
    token = service.login("fan", "fan-pass").token
    body, signature = token.split(".")
    forged_body = body[:-2] + ("AA" if body[-2:] != "AA" else "BB")
    with pytest.raises(AuthError):
        service.verify(f"{forged_body}.{signature}")
    with pytest.raises(AuthError):
        AuthService(USERS, "x" * 40).verify(token)


def test_expired_token_is_rejected() -> None:
    clock = Clock()
    service = AuthService(USERS, SECRET, clock=clock)
    token = service.login("fan", "fan-pass").token
    clock.now += TOKEN_TTL_S + 1
    with pytest.raises(AuthError):
        service.verify(token)


def test_short_secret_is_refused() -> None:
    with pytest.raises(ValueError):
        AuthService(USERS, "short")


def test_documented_demo_accounts_work() -> None:
    """Las cuentas de docs/persona-4-api-y-frontend/README.md existen en demo-users.json."""
    from match_intelligence.adapters.http.auth_router import DEFAULT_USERS_FILE, _load_users

    service = AuthService(_load_users(DEFAULT_USERS_FILE), SECRET)
    assert service.login("aficionado", "aficionado-demo-2026").user.role is Role.FAN
    assert service.login("analista", "analista-demo-2026").user.role is Role.ANALYST


# ----- HTTP -----------------------------------------------------------------

def test_login_me_and_logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "fan", "password": "fan-pass"})
    body = response.json()
    assert body["token_type"] == "bearer" and body["expires_at"] > 0
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json() == {"username": "fan", "display_name": "Fan", "role": "fan"}
    assert client.post("/api/v1/auth/logout", headers=headers).json() == {"detail": "Sesión cerrada"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_http_failed_login_reports_attempts_then_429(client: TestClient) -> None:
    for expected_left in range(MAX_FAILED_ATTEMPTS - 1, 0, -1):
        response = client.post("/api/v1/auth/login", json={"username": "pro", "password": "x"})
        assert response.status_code == 401
        assert response.json()["attempts_left"] == expected_left
    locked = client.post("/api/v1/auth/login", json={"username": "pro", "password": "x"})
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) == locked.json()["retry_after_s"] > 0
