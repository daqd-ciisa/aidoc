"""Capa 2 — Smoke E2E contra PCAI REAL (gated, no corre en CI).

A diferencia de la Capa 1, esto NO usa la app en proceso ni los fakes: golpea el
stack ya levantado (``docker compose up``) en ``AIDOC_BASE_URL`` con los endpoints
NIM reales. Por eso las aserciones son laxas/estructurales (hay respuesta, hay
citas, latencia razonable) — el contenido del modelo no es determinista.

Requisitos para correrlo:
  • VPN a PCAI + tokens vigentes en el ``.env`` del backend.
  • Stack arriba y sano (``GET /api/health/deps`` en verde).
  • Un usuario válido para login.

Activar:  AIDOC_RUN_PCAI=1 \
          AIDOC_BASE_URL=http://localhost:8000 \
          AIDOC_USER=admin@org.com AIDOC_PASS=... \
          pytest -m pcai
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.pcai

_RUN = os.getenv("AIDOC_RUN_PCAI") == "1"


@pytest.mark.skipif(not _RUN, reason="define AIDOC_RUN_PCAI=1 y corré con -m pcai")
async def test_pcai_smoke():
    import httpx

    base = os.environ["AIDOC_BASE_URL"]
    user = os.environ["AIDOC_USER"]
    pwd = os.environ["AIDOC_PASS"]

    async with httpx.AsyncClient(base_url=base, timeout=60, verify=False) as c:
        # Salud de dependencias reales.
        deps = await c.get("/api/health/deps")
        assert deps.json()["status"] == "ok", deps.text

        # Login real.
        login = await c.post(
            "/api/auth/login", json={"email": user, "password": pwd}
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # TODO(Capa 2): subir un doc real, esperar 'indexed' (polling), chatear y
        # verificar respuesta con ≥1 cita en <10s, generar cotización y PDF.
        # Aserciones estructurales, nunca texto exacto del modelo.
        docs = await c.get("/api/documents", headers=headers)
        assert docs.status_code == 200
