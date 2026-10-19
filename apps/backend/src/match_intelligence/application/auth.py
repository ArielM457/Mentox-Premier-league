"""Inicio de sesión de la demo con dos perfiles: aficionado y analista profesional.

Las contraseñas se guardan como PBKDF2-SHA256 con sal y los tokens son
HMAC-SHA256 firmados con un secreto del servidor. No usa dependencias
externas. Es suficiente para separar permisos en la demo; un despliegue real
necesitaría un proveedor de identidad.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from enum import StrEnum

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_S = 8 * 60 * 60


class Role(StrEnum):
    FAN = "fan"
    ANALYST = "analyst"


class AuthError(Exception):
    """Credenciales o token inválidos."""


@dataclass(frozen=True)
class User:
    username: str
    display_name: str
    role: Role


@dataclass(frozen=True)
class StoredUser:
    user: User
    salt: str
    password_hash: str


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return digest.hex()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class AuthService:
    def __init__(self, users: list[StoredUser], secret: str, *, clock=time.time) -> None:
        if len(secret) < 32:
            raise ValueError("El secreto de los tokens necesita al menos 32 caracteres")
        self._users = {stored.user.username: stored for stored in users}
        self._secret = secret.encode()
        self._clock = clock

    def login(self, username: str, password: str) -> tuple[str, User]:
        stored = self._users.get(username.strip().lower())
        # Se calcula el hash aunque el usuario no exista para no revelar cuáles existen por tiempo.
        expected = stored.password_hash if stored else "0" * 64
        actual = hash_password(password, stored.salt if stored else "missing-user")
        if not stored or not hmac.compare_digest(actual, expected):
            raise AuthError("Usuario o contraseña incorrectos")
        return self._issue(stored.user), stored.user

    def verify(self, token: str) -> User:
        try:
            body, signature = token.split(".", 1)
        except ValueError as error:
            raise AuthError("Token mal formado") from error
        expected = _b64(hmac.new(self._secret, body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise AuthError("Firma del token inválida")
        payload = json.loads(_unb64(body))
        if payload["exp"] < self._clock():
            raise AuthError("La sesión expiró")
        stored = self._users.get(payload["sub"])
        if stored is None or stored.user.role.value != payload["role"]:
            raise AuthError("El usuario del token ya no existe")
        return stored.user

    def _issue(self, user: User) -> str:
        payload = {"sub": user.username, "role": user.role.value, "exp": int(self._clock()) + TOKEN_TTL_S}
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        signature = _b64(hmac.new(self._secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{signature}"
