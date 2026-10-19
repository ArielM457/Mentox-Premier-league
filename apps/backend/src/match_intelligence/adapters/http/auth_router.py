"""Rutas de sesión y dependencias de permisos."""

import json
import os
import secrets
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from match_intelligence.application.auth import AuthError, AuthService, Role, StoredUser, User

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


def current_user(request: Request, auth: Auth) -> User:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Necesitas iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
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
    user: UserResponse


def _user(user: User) -> UserResponse:
    return UserResponse(username=user.username, display_name=user.display_name, role=user.role.value)


router = APIRouter(prefix="/api/v1/auth", tags=["Sesión"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión como aficionado o analista",
    responses={401: {"description": "Usuario o contraseña incorrectos"}},
)
def login(body: LoginRequest, auth: Auth) -> LoginResponse:
    try:
        token, user = auth.login(body.username, body.password)
    except AuthError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return LoginResponse(token=token, user=_user(user))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Usuario de la sesión actual",
    responses={401: {"description": "Sin sesión o sesión vencida"}},
)
def me(user: Annotated[User, Depends(current_user)]) -> UserResponse:
    return _user(user)
