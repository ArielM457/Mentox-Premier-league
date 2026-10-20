"""Rutas de sesión y dependencias de permisos."""

import json
import os
import secrets
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.auth import (
    FAILURE_WINDOW_S,
    LOCKOUT_S,
    MAX_FAILED_ATTEMPTS,
    AuthError,
    AuthService,
    LockedError,
    Role,
    StoredUser,
    User,
)

DEFAULT_USERS_FILE = Path(__file__).resolve().parents[4] / "demo-users.json"


def _load_users(path: Path) -> list[StoredUser]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        StoredUser(
            user=User(username=item["username"], display_name=item["display_name"], role=Role(item["role"])),
            salt=item["salt"],
            password_hash=item["password_hash"],
        )
        for item in data["users"]
    ]


_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Usuarios desde MATCH_DEMO_USERS_FILE y secreto desde MATCH_AUTH_SECRET.

    Sin secreto configurado se genera uno al arrancar: las sesiones duran
    mientras el proceso siga vivo.
    """
    global _service
    if _service is None:
        path = Path(os.environ.get("MATCH_DEMO_USERS_FILE", DEFAULT_USERS_FILE))
        secret = os.environ.get("MATCH_AUTH_SECRET") or secrets.token_hex(32)
        _service = AuthService(_load_users(path), secret)
    return _service


Auth = Annotated[AuthService, Depends(get_auth_service)]


def bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Necesitas iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
    return token


def current_user(token: Annotated[str, Depends(bearer_token)], auth: Auth) -> User:
    try:
        return auth.verify(token)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error), headers={"WWW-Authenticate": "Bearer"}) from error


def require_analyst(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role is not Role.ANALYST:
        raise HTTPException(status_code=403, detail="Solo un analista profesional puede usar esta función")
    return user


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    username: str
    display_name: str
    role: Literal["fan", "analyst"]


class LoginResponse(BaseModel):
    token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: int = Field(description="Vencimiento de la sesión en segundos Unix")
    user: UserResponse


class LoginError(BaseModel):
    detail: str
    attempts_left: int | None = Field(default=None, description="Intentos antes del bloqueo temporal")
    retry_after_s: int | None = Field(default=None, description="Segundos hasta poder volver a intentarlo")


class LogoutResponse(BaseModel):
    detail: str


def _user(user: User) -> UserResponse:
    return UserResponse(username=user.username, display_name=user.display_name, role=user.role.value)


router = APIRouter(prefix="/api/v1/auth", tags=["Sesión"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión como aficionado o analista",
    description=(
        f"Tras {MAX_FAILED_ATTEMPTS} intentos fallidos en {FAILURE_WINDOW_S // 60} minutos la cuenta se bloquea "
        f"{LOCKOUT_S // 60} minutos y responde 429 con la cabecera Retry-After."
    ),
    responses={
        401: {"model": LoginError, "description": "Usuario o contraseña incorrectos"},
        429: {"model": LoginError, "description": "Demasiados intentos fallidos"},
    },
)
def login(body: LoginRequest, auth: Auth) -> LoginResponse | JSONResponse:
    try:
        session = auth.login(body.username, body.password)
    except LockedError as error:
        return JSONResponse(
            status_code=429,
            content=LoginError(detail=str(error), retry_after_s=error.retry_after_s).model_dump(),
            headers={"Retry-After": str(error.retry_after_s)},
        )
    except AuthError as error:
        return JSONResponse(
            status_code=401,
            content=LoginError(detail=str(error), attempts_left=error.attempts_left).model_dump(),
        )
    return LoginResponse(token=session.token, expires_at=session.expires_at, user=_user(session.user))


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Cerrar sesión",
    description="Revoca el token en el servidor: deja de servir aunque no haya vencido.",
    responses={401: {"description": "Sin sesión o sesión ya cerrada"}},
)
def logout(token: Annotated[str, Depends(bearer_token)], auth: Auth) -> LogoutResponse:
    try:
        auth.logout(token)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return LogoutResponse(detail="Sesión cerrada")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Usuario de la sesión actual",
    responses={401: {"description": "Sin sesión o sesión vencida"}},
)
def me(user: Annotated[User, Depends(current_user)]) -> UserResponse:
    return _user(user)
