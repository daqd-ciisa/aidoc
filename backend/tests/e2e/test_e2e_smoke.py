"""Capa 1 — E2E de plumbing (mocked LLM/embeddings, sin PCAI).

Ejercita el flujo completo del POC con aserciones ESTRUCTURALES:
  login → upload → indexado → chat RAG (SSE) → cotización guiada → export PDF.

Mide la cañería real (FastAPI, parsers, chunker, Qdrant, storage, persistencia),
no la calidad del modelo. Corre en CI sin tokens ni red. La validación contra el
modelo real vive en la Capa 2 (``test_e2e_pcai.py``, marcada ``pcai``).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

DOC_TEXT = (
    "Cotización de servicios para el cliente ACME.\n"
    "Servicio: Soporte técnico mensual.\n"
    "Cantidad: 1. Precio unitario: 1000 MXN. Importe: 1000 MXN.\n"
    "Subtotal: 1000 MXN. IVA (16%): 160 MXN. Total: 1160 MXN.\n"
    "Vigencia: 30 días. Condiciones: pago a 30 días.\n"
)


async def _read_sse(client, headers, payload):
    """Lanza POST /api/chat y devuelve (eventos, texto_respuesta)."""
    events: list[str] = []
    answer = ""
    async with client.stream(
        "POST", "/api/chat", headers=headers, json=payload
    ) as resp:
        assert resp.status_code == 200, resp.status_code
        current = None
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                current = line.split(":", 1)[1].strip()
                events.append(current)
            elif line.startswith("data:") and current == "token":
                import json

                answer += json.loads(line.split(":", 1)[1].strip()).get("text", "")
    return events, answer


# ── Pruebas atómicas ──────────────────────────────────────────────────────────────


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_requires_auth(client):
    """Sin token, los endpoints de datos responden 401/403."""
    resp = await client.get("/api/documents")
    assert resp.status_code in (401, 403)


async def test_login(auth):
    assert auth["headers"]["Authorization"].startswith("Bearer ")


# ── Flujo E2E completo ──────────────────────────────────────────────────────────


async def _upload_doc(client, headers, name="cotizacion_acme.txt"):
    resp = await client.post(
        "/api/documents",
        headers=headers,
        files={"files": (name, DOC_TEXT.encode(), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    docs = resp.json()["documents"]
    assert len(docs) == 1
    return docs[0]["id"]


async def test_upload_and_index(client, auth):
    """Paso 1-3: subir un documento y verificar que queda indexado con chunks."""
    doc_id = await _upload_doc(client, auth["headers"])

    resp = await client.get(f"/api/documents/{doc_id}", headers=auth["headers"])
    assert resp.status_code == 200
    doc = resp.json()
    # El indexado corre inline (fake enqueue) → debe terminar en 'indexed'.
    assert doc["status"] == "indexed", doc
    assert doc["chunk_count"] >= 1


async def test_chat_rag_sse(client, auth):
    """Paso 5: chat RAG por SSE devuelve la secuencia meta→citations→token*→done."""
    await _upload_doc(client, auth["headers"])

    events, answer = await _read_sse(
        client,
        auth["headers"],
        {"message": "¿Cuánto cuesta el servicio?"},
    )
    assert "meta" in events
    assert "citations" in events
    assert "token" in events
    assert "done" in events
    assert "error" not in events
    assert answer.strip()  # se reconstruyó una respuesta


async def test_chat_history_persists(client, auth):
    """Paso 6: la conversación queda guardada y es navegable."""
    await _upload_doc(client, auth["headers"])
    await _read_sse(client, auth["headers"], {"message": "Hola, ¿qué dice el documento?"})

    resp = await client.get("/api/chat/sessions", headers=auth["headers"])
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1

    detail = await client.get(
        f"/api/chat/sessions/{sessions[0]['id']}", headers=auth["headers"]
    )
    assert detail.status_code == 200
    msgs = detail.json()["messages"]
    roles = {m["role"] for m in msgs}
    assert "user" in roles and "assistant" in roles


async def test_guided_quote_and_pdf(client, auth):
    """Paso 7: cotización guiada por precedente + export a PDF."""
    doc_id = await _upload_doc(client, auth["headers"])

    # Paso 1 del flujo guiado: buscar precedentes parecidos al pedido.
    resp = await client.post(
        "/api/quotes/precedents",
        headers=auth["headers"],
        json={"request": "Necesito una cotización de soporte técnico"},
    )
    assert resp.status_code == 200, resp.text
    precedents = resp.json()["precedents"]
    assert len(precedents) >= 1
    assert precedents[0]["document_id"] == doc_id

    # Paso 2: generar la nueva cotización usando el precedente como plantilla.
    resp = await client.post(
        "/api/quotes/from-precedent",
        headers=auth["headers"],
        json={
            "request": "Soporte técnico para mi empresa",
            "document_ids": [doc_id],
        },
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    quote_id = result["quote_id"]
    assert result["quote"]["items"], "la cotización debe tener ítems"
    assert result["based_on"]["document_id"] == doc_id

    # Export a PDF: bytes válidos de PDF.
    pdf = await client.get(
        f"/api/quotes/{quote_id}/pdf", headers=auth["headers"]
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:5] == b"%PDF-"


async def test_quote_from_scratch(client, auth):
    """Cotización desde cero (sin documentos): esqueleto con ítems, precios en null."""
    resp = await client.post(
        "/api/quotes/from-scratch",
        headers=auth["headers"],
        json={"request": "Cotización de instalación de red para 3 oficinas"},
    )
    assert resp.status_code == 200, resp.text
    assert "quote_id" in resp.json()


async def test_tenant_isolation(client, auth):
    """Un documento de un tenant no es visible para otro (aislamiento por org)."""
    doc_id = await _upload_doc(client, auth["headers"])

    # Segundo tenant con su propio token.
    import uuid

    from app.auth.security import hash_password
    from app.db.models.organization import Organization
    from app.db.models.user import ROLE_ADMIN, User
    from app.db.session import AsyncSessionLocal

    other_org = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        db.add(Organization(id=other_org, slug="other-org", name="Other"))
        db.add(
            User(
                id=str(uuid.uuid4()),
                email="other@test.com",
                password_hash=hash_password("password123"),
                organization_id=other_org,
                role=ROLE_ADMIN,
                is_active=True,
            )
        )
        await db.commit()
    login = await client.post(
        "/api/auth/login",
        json={"email": "other@test.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # El otro tenant no ve el documento, ni puede accederlo por id.
    listing = await client.get("/api/documents", headers=other_headers)
    assert all(d["id"] != doc_id for d in listing.json())
    direct = await client.get(f"/api/documents/{doc_id}", headers=other_headers)
    assert direct.status_code == 404
