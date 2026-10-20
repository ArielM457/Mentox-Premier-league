"""Inicio de sesión de la demo con dos perfiles: aficionado y analista profesional.

- Contraseñas guardadas como PBKDF2-SHA256 con sal; nunca en texto plano.
- Tokens HMAC-SHA256 con identificador propio (``jti``), emisión y vencimiento.
- Cerrar sesión revoca el token en el servidor.
- Tras varios intentos fallidos la cuenta se bloquea unos minutos.

No usa dependencias externas y guarda revocaciones e intentos en memoria. Es
suficiente para la demo; un despliegue real necesitaría un proveedor de
identidad y un almacén compartido.
"""

import base64
import hashlib
import hmac
import json
import math
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_S = 8 * 60 * 60
MAX_FAILED_ATTEMPTS = 5
FAILURE_WINDOW_S = 15 * 60
LOCKOUT_S = 5 * 60


class Role(StrEnum):
    FAN = "fan"
    ANALYST = "analyst"


class AuthError(Exception):
    """Credenciales o token inválidos."""

    def __init__(self, message: str, *, attempts_left: int | None = None) -> None:
        super().__init__(message)
        self.attempts_left = attempts_left


class LockedError(AuthError):
    """Demasiados intentos fallidos: la cuenta está bloqueada un tiempo."""

    def __init__(self, retry_after_s: int) -> None:
        super().__init__(f"Demasiados intentos fallidos. Vuelve a intentarlo en {retry_after_s} segundos.")
        self.retry_after_s = retry_after_s


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


@dataclass(frozen=True)
class Session:
    token: str
    user: User
    expires_at: int


@dataclass
class _Attempts:
    failures: list[float] = field(default_factory=list)
    locked_until: float = 0.0


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return digest.hex()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class AuthService:
    def __init__(
        self,
        users: list[StoredUser],
        secret: str,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("El secreto de los tokens necesita al menos 32 caracteres")
        self._users = {stored.user.username: stored for stored in users}
        self._secret = secret.encode()
        self._clock = clock
        self._attempts: dict[str, _Attempts] = {}
        self._revoked: dict[str, float] = {}
        self._lock = threading.Lock()

    # ----- inicio y cierre de sesión ------------------------------------------
    def login(self, username: str, password: str) -> Session:
        key = username.strip().lower()
        now = self._clock()
        with self._lock:
            attempts = self._attempts.setdefault(key, _Attempts())
            if attempts.locked_until > now:
                raise LockedError(math.ceil(attempts.locked_until - now))

        stored = self._users.get(key)
        # Se calcula el hash aunque el usuario no exista para no revelar cuáles existen por tiempo.
        expected = stored.password_hash if stored else "0" * 64
        actual = hash_password(password, stored.salt if stored else "missing-user")
        valid = stored is not None and hmac.compare_digest(actual, expected)

        with self._lock:
            if valid:
                self._attempts.pop(key, None)
                return self._issue(stored.user, now)
            attempts.failures = [t for t in attempts.failures if now - t < FAILURE_WINDOW_S] + [now]
            left = MAX_FAILED_ATTEMPTS - len(attempts.failures)
            if left <= 0:
                attempts.failures = []
                attempts.locked_until = now + LOCKOUT_S
                raise LockedError(LOCKOUT_S)
        raise AuthError("Usuario o contraseña incorrectos", attempts_left=left)

    def logout(self, token: str) -> None:
        payload = self._payload(token)
        with self._lock:
            self._revoked[payload["jti"]] = payload["exp"]
            self._forget_expired()

    def verify(self, token: str) -> User:
        payload = self._payload(token)
        with self._lock:
            if payload["jti"] in self._revoked:
                raise AuthError("La sesión se cerró")
        stored = self._users.get(payload["sub"])
        if stored is None or stored.user.role.value != payload["role"]:
            raise AuthError("El usuario del token ya no existe")
        return stored.user

    # ----- tokens ---------------------------------------------------------
    def _issue(self, user: User, now: float) -> Session:
        expires_at = int(now) + TOKEN_TTL_S
        payload = {
            "sub": user.username,
            "role": user.role.value,
            "iat": int(now),
            "exp": expires_at,
            "jti": secrets.token_urlsafe(16),
        }
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        return Session(token=f"{body}.{self._sign(body)}", user=user, expires_at=expires_at)

    def _sign(self, body: str) -> str:
        return _b64(hmac.new(self._secret, body.encode(), hashlib.sha256).digest())

    def _payload(self, token: str) -> dict:
        try:
            body, signature = token.split(".", 1)
        except ValueError as error:
            raise AuthError("Token mal formado") from error
        if not hmac.compare_digest(signature, self._sign(body)):
            raise AuthError("Firma del token inválida")
        try:
            payload = json.loads(_unb64(body))
        except ValueError as error:
            raise AuthError("Token mal formado") from error
        if payload.get("exp", 0) < self._clock():
            raise AuthError("La sesión expiró")
        if "jti" not in payload:
            raise AuthError("Token mal formado")
        return payload

    def _forget_expired(self) -> None:
        now = self._clock()
        for jti in [jti for jti, exp in self._revoked.items() if exp < now]:
            del self._revoked[jti]
