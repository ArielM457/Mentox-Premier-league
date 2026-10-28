"""La revisión editorial solo acepta sesiones de Supabase Auth con el rol de editor."""

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.testclient import TestClient

import editor_tokens
from match_intelligence.adapters.http import editor_auth
from match_intelligence.adapters.http.editor_auth import Editor, EditorVerifier, get_editor_verifier
from match_intelligence.adapters.http.registry import DEMO_MATCH_ID, _default_registry, get_registry
from match_intelligence.main import app

BASE = f"/api/v1/matches/{DEMO_MATCH_ID}"


def rejection(token: str) -> int:
    with pytest.raises(HTTPException) as error:
        editor_tokens.verifier().verify(token)
    return error.value.status_code


def test_editor_token_identifies_the_reviewer() -> None:
    assert editor_tokens.verifier().verify(editor_tokens.token()) == Editor(editor_tokens.EDITOR_ID)


@pytest.mark.parametrize(
    "changes",
    [
        {"exp": int(time.time()) - 60},
        {"iss": "https://otro-proyecto.supabase.co/auth/v1"},
        {"aud": "anon"},
        {"sub": None},
        {"key": ec.generate_private_key(ec.SECP256R1())},
    ],
    ids=["vencido", "otro-emisor", "otra-audiencia", "sin-usuario", "otra-clave"],
)
def test_invalid_sessions_are_unauthorized(changes: dict) -> None:
    assert rejection(editor_tokens.token(**changes)) == 401


def test_symmetric_tokens_and_garbage_are_unauthorized() -> None:
    forged = jwt.encode({"sub": "x", "app_metadata": {"role": "editor"}}, "secreto-compartido-de-32-bytes!!", algorithm="HS256")
    assert rejection(forged) == 401
    assert rejection("no-es-un-token") == 401


@pytest.mark.parametrize(
    "changes",
    [
        {"app_metadata": {"provider": "email"}},
        {"app_metadata": None},
        # user_metadata lo edita el propio usuario: no concede permisos.
        {"app_metadata": {"provider": "email"}, "user_metadata": {"role": "editor"}},
    ],
    ids=["sin-rol", "sin-app-metadata", "rol-en-user-metadata"],
)
def test_accounts_without_the_editor_role_are_forbidden(changes: dict) -> None:
    assert rejection(editor_tokens.token(**changes)) == 403


def test_environment_derives_issuer_and_jwks_from_the_project_url(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[str] = []

    class FakeJWKClient:
        def __init__(self, uri: str, **_options) -> None:
            requested.append(uri)

        def get_signing_key_from_jwt(self, _token: str) -> SimpleNamespace:
            return SimpleNamespace(key=editor_tokens.SIGNING_KEY.public_key())

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert EditorVerifier.from_environment() is None

    monkeypatch.setenv("SUPABASE_URL", "https://proyecto-de-prueba.supabase.co/")
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.setattr(editor_auth.jwt, "PyJWKClient", FakeJWKClient)
    verifier = EditorVerifier.from_environment()

    assert requested == ["https://proyecto-de-prueba.supabase.co/auth/v1/.well-known/jwks.json"]
    assert verifier.verify(editor_tokens.token()).user_id == editor_tokens.EDITOR_ID


@pytest.fixture
def client():
    registry = _default_registry()
    app.dependency_overrides[get_registry] = lambda: registry
    app.dependency_overrides[get_editor_verifier] = editor_tokens.verifier
    yield TestClient(app)
    app.dependency_overrides.clear()


def pending_summary(client: TestClient) -> str:
    return client.get(f"{BASE}/summary").json()["draft"]["draft_id"]


def test_review_without_session_is_rejected_and_keeps_the_draft_pending(client: TestClient) -> None:
    draft_id = pending_summary(client)
    anonymous = client.post(f"{BASE}/editorial/{draft_id}/review", json={"decision": "approve"})
    reader = client.post(
        f"{BASE}/editorial/{draft_id}/review",
        json={"decision": "approve"},
        headers=editor_tokens.headers(editor_tokens.token(app_metadata={"provider": "email"})),
    )

    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"] == "Bearer"
    assert reader.status_code == 403
    assert client.get(f"{BASE}/editorial").json()[0]["status"] == "pending"


def test_reviewer_comes_from_the_session_not_from_the_body(client: TestClient) -> None:
    draft_id = pending_summary(client)
    impersonation = client.post(
        f"{BASE}/editorial/{draft_id}/review",
        json={"decision": "approve", "reviewer": "Otra persona"},
        headers=editor_tokens.headers(),
    )
    approved = client.post(
        f"{BASE}/editorial/{draft_id}/review", json={"decision": "approve"}, headers=editor_tokens.headers()
    )

    assert impersonation.status_code == 422
    assert approved.status_code == 200
    assert approved.json()["reviewer"] == editor_tokens.EDITOR_ID


def test_review_is_closed_when_supabase_auth_is_not_configured(client: TestClient) -> None:
    app.dependency_overrides[get_editor_verifier] = lambda: None
    draft_id = pending_summary(client)
    response = client.post(
        f"{BASE}/editorial/{draft_id}/review", json={"decision": "approve"}, headers=editor_tokens.headers()
    )

    assert response.status_code == 503
    assert "SUPABASE_URL" in response.json()["detail"]


def test_highlight_review_requires_an_editor(client: TestClient) -> None:
    response = client.post(f"{BASE}/highlights/cualquiera/review", json={"decision": "approved"})
    assert response.status_code == 401
