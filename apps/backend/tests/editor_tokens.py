"""Tokens de Supabase Auth firmados con una clave de prueba, como los que recibe la revisión editorial."""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from match_intelligence.adapters.http.editor_auth import EditorVerifier

ISSUER = "https://proyecto-de-prueba.supabase.co/auth/v1"
EDITOR_ID = "6f1c2a4e-0000-4000-8000-00000000e0e0"
SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())


def token(*, key=SIGNING_KEY, algorithm: str = "ES256", **changes) -> str:
    """Token de editor válido; ``changes`` reemplaza claims y ``None`` los quita."""
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": "authenticated",
        "sub": EDITOR_ID,
        "exp": now + 600,
        "iat": now,
        "role": "authenticated",
        "app_metadata": {"provider": "email", "role": "editor"},
    }
    claims.update(changes)
    return jwt.encode({name: value for name, value in claims.items() if value is not None}, key, algorithm=algorithm)


def verifier() -> EditorVerifier:
    return EditorVerifier(ISSUER, lambda _token: SIGNING_KEY.public_key())


def headers(value: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {value or token()}"}
