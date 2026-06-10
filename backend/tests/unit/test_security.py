"""Unit · hashing de passwords y emisión/validación de JWT (app.auth.security)."""
from __future__ import annotations

import jwt
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_is_salted_and_verifiable():
    h = hash_password("secreto123")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("secreto123", h)
    # Mismo password, dos hashes distintos (salt aleatorio).
    assert hash_password("secreto123") != h


def test_verify_password_rejects_wrong_and_malformed():
    h = hash_password("correcto")
    assert not verify_password("incorrecto", h)
    assert not verify_password("correcto", "formato-invalido")
    assert not verify_password("correcto", "")


def test_jwt_round_trip_carries_claims():
    token = create_access_token(sub="user-1", org="org-9", role="admin")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["org"] == "org-9"
    assert payload["role"] == "admin"


def test_jwt_expired_is_rejected():
    token = create_access_token(
        sub="u", org=None, role="member", expires_minutes=-1
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_jwt_tampered_signature_is_rejected():
    token = create_access_token(sub="u", org=None, role="member")
    tampered = token[:-3] + ("abc" if token[-3:] != "abc" else "xyz")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)
