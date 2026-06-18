"""Integración · administración de auth vía HTTP: cambio de contraseña y altas.

Ejercita los endpoints de ``app.api.auth`` contra la app ASGI (fixtures ``client`` y
``auth`` del conftest): el admin cambia su propia contraseña y da de alta usuarios de
su organización. No toca PCAI (auth no usa embeddings/LLM).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current(client, auth):
    resp = await client.post(
        "/api/auth/change-password",
        headers=auth["headers"],
        json={"current_password": "incorrecta", "new_password": "nuevaclave1"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_change_password_updates_and_reauthenticates(client, auth):
    # La contraseña actual del admin de la fixture es "password123".
    resp = await client.post(
        "/api/auth/change-password",
        headers=auth["headers"],
        json={"current_password": "password123", "new_password": "nuevaclave1"},
    )
    assert resp.status_code == 200, resp.text

    # La vieja ya no sirve...
    old = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert old.status_code == 401
    # ...y la nueva sí.
    new = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "nuevaclave1"},
    )
    assert new.status_code == 200, new.text


@pytest.mark.asyncio
async def test_change_password_enforces_min_length(client, auth):
    resp = await client.post(
        "/api/auth/change-password",
        headers=auth["headers"],
        json={"current_password": "password123", "new_password": "corta"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_admin_creates_and_lists_users_in_own_org(client, auth):
    create = await client.post(
        "/api/auth/users",
        headers=auth["headers"],
        json={"email": "nuevo@test.com", "password": "password123", "role": "member"},
    )
    assert create.status_code == 200, create.text
    assert create.json()["organization_id"] == auth["tenant_id"]

    listed = await client.get("/api/auth/users", headers=auth["headers"])
    assert listed.status_code == 200, listed.text
    emails = {u["email"] for u in listed.json()}
    assert {"admin@test.com", "nuevo@test.com"} <= emails


@pytest.mark.asyncio
async def test_member_cannot_create_users(client, auth):
    # Damos de alta un member y nos logueamos como él.
    await client.post(
        "/api/auth/users",
        headers=auth["headers"],
        json={"email": "miembro@test.com", "password": "password123", "role": "member"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"email": "miembro@test.com", "password": "password123"},
    )
    token = login.json()["access_token"]

    resp = await client.post(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "otro@test.com", "password": "password123", "role": "member"},
    )
    assert resp.status_code == 403, resp.text
