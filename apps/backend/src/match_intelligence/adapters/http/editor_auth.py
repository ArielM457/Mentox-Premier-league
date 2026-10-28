"""Identidad de quien revisa: sesiones de Supabase Auth con el rol de editor.

Las decisiones editoriales deciden qué se publica y se guardan, así que la identidad sale del
token firmado y no del cuerpo de la petición. Supabase firma los tokens con claves asimétricas
que se leen de su JWKS. El rol vive en ``app_metadata``, que el usuario no puede cambiar: solo
un administrador del proyecto lo asigna. Sin ``SUPABASE_URL`` la revisión queda cerrada.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .match_schemas import ErrorResponse

EDITOR_ROLE = "editor"
AUDIENCE = "authenticated"
# Nunca HS256: con claves asimétricas, aceptar un algoritmo simétrico permitiría firmar con la clave pública.
ALGORITHMS = ["ES256", "RS256"]

EDITOR_ERRORS = {
    401: {"model": ErrorResponse, "description": "Falta la sesión de editor o no es válida"},
    403: {"model": ErrorResponse, "description": "La cuenta no tiene el rol de editor"},
    503: {"model": ErrorResponse, "description": "Supabase Auth no está configurado o no responde"},
}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Editor:
    user_id: str


class EditorVerifier:
    def __init__(self, issuer: str, signing_key: Callable[[str], Any]) -> None:
        self._issuer = issuer
        self._signing_key = signing_key

    @classmethod
    def from_environment(cls) -> "EditorVerifier | None":
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        if not url:
            return None
        jwks_url = os.getenv("SUPABASE_JWKS_URL", "").strip() or f"{url}/auth/v1/.well-known/jwks.json"
        client = jwt.PyJWKClient(jwks_url, cache_keys=True, timeout=5)
        return cls(f"{url}/auth/v1", lambda token: client.get_signing_key_from_jwt(token).key)

    def verify(self, token: str) -> Editor:
        try:
            claims = jwt.decode(
                token,
                self._signing_key(token),
                algorithms=ALGORITHMS,
                audience=AUDIENCE,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWKClientConnectionError as error:
            raise HTTPException(503, "No se pudo comprobar la sesión con Supabase Auth") from error
        except jwt.PyJWTError as error:
            raise _unauthorized("La sesión de editor no es válida o venció") from error
        if (claims.get("app_metadata") or {}).get("role") != EDITOR_ROLE:
            raise HTTPException(403, "Esta cuenta no tiene el rol de editor")
        return Editor(user_id=claims["sub"])


@lru_cache(maxsize=1)
def get_editor_verifier() -> EditorVerifier | None:
    return EditorVerifier.from_environment()


def require_editor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[EditorVerifier | None, Depends(get_editor_verifier)],
) -> Editor:
    if verifier is None:
        raise HTTPException(503, "La revisión editorial necesita Supabase Auth: configure SUPABASE_URL")
    if credentials is None:
        raise _unauthorized("Inicie sesión como editor para revisar")
    return verifier.verify(credentials.credentials)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


CurrentEditor = Annotated[Editor, Depends(require_editor)]
