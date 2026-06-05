"""Hashing de passwords (PBKDF2, stdlib) y emisión/validación de JWT."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_ALGO = "HS256"
_PBKDF2_ROUNDS = 200_000


# ── Passwords ─────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Devuelve ``pbkdf2_sha256$rounds$salt$hash`` (sin dependencias nativas)."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ROUNDS,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds_s, salt_b64, hash_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds_s))
        return hmac.compare_digest(dk, expected)
    except Exception:  # noqa: BLE001 — formato inesperado => no autentica
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────


def create_access_token(
    *, sub: str, org: str | None, role: str, expires_minutes: int | None = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": sub, "org": org, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGO)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida (firma + expiración). Lanza ``jwt.PyJWTError`` si falla."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGO])
