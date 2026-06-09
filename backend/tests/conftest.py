"""Configuración y fixtures de la Capa 1 (E2E de plumbing, sin PCAI).

Estrategia:
  • DB: SQLite (aiosqlite) en un archivo temporal → se comparte entre la sesión del
    request, el chat y el "worker" inline. Se setea ``DATABASE_URL`` por env ANTES de
    importar la app (la env var gana sobre el .env por precedencia de pydantic).
  • Qdrant: cliente local en memoria (``:memory:``) → hermético, sin contenedor.
  • Storage (MinIO/S3): dict en memoria.
  • Embeddings y LLM: fakes deterministas (ver ``tests/fakes.py``).
  • Indexado: el ``enqueue_index`` real (ARQ/Redis) se reemplaza por una versión que
    corre el indexado INLINE llamando a la tarea real del worker → mismo código de
    pipeline, sin Redis ni proceso aparte.

Correr desde ``backend/``:  ``pytest``  (o ``pytest -m "not pcai"``).
"""
from __future__ import annotations

import importlib
import os
import pathlib
import tempfile

# ── 1. Configurar el entorno ANTES de importar la app ─────────────────────────────
# DB SQLite en archivo temporal (compartido entre conexiones/sesiones del test).
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "aidoc_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
# Secreto estable para firmar/validar JWT durante los tests.
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long-xyz")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402


# ── 2. Parchear los servicios remotos (autouse, por test) ─────────────────────────


@pytest.fixture(autouse=True)
def _patch_services(monkeypatch):
    """Reemplaza Qdrant/Storage/Embeddings/LLM/cola por dobles locales."""
    from qdrant_client import QdrantClient

    from tests.fakes import FakeChatLLM, FakeEmbeddings

    # --- Qdrant en memoria ---
    qclient = QdrantClient(location=":memory:")
    import app.services.qdrant as qmod

    monkeypatch.setattr(qmod, "get_qdrant_client", lambda: qclient)
    qmod.ensure_collection()  # crea la colección sobre el cliente en memoria

    # --- Storage en memoria ---
    import app.services.storage as smod

    store: dict[str, bytes] = {}
    monkeypatch.setattr(smod, "ensure_bucket", lambda: None)
    monkeypatch.setattr(
        smod, "upload_bytes",
        lambda key, data, content_type=None: store.__setitem__(key, data),
    )
    monkeypatch.setattr(smod, "download_bytes", lambda key: store[key])
    monkeypatch.setattr(smod, "delete_object", lambda key: store.pop(key, None))

    # --- Embeddings (donde se usan: rag y pipeline) ---
    fake_emb = FakeEmbeddings()
    for mod_name in ("app.chat.rag", "app.ingestion.pipeline"):
        monkeypatch.setattr(
            importlib.import_module(mod_name), "get_embeddings", lambda: fake_emb
        )

    # --- LLM (donde se usa: chat, extractor, summarizer, proposal) ---
    def fake_get_chat_llm(**_kwargs):
        return FakeChatLLM()

    for mod_name in (
        "app.api.chat",
        "app.quotes.extractor",
        "app.quotes.summarizer",
        "app.quotes.proposal",
    ):
        monkeypatch.setattr(
            importlib.import_module(mod_name),
            "get_chat_llm",
            fake_get_chat_llm,
            raising=False,
        )

    # --- Cola ARQ → indexado INLINE (corre la tarea real del worker) ---
    async def fake_enqueue(document_id: str) -> str:
        from app.workers.tasks import index_document

        await index_document({}, document_id)
        return f"test-job-{document_id[:8]}"

    monkeypatch.setattr(
        importlib.import_module("app.ingestion.intake"), "enqueue_index", fake_enqueue
    )
    monkeypatch.setattr(
        importlib.import_module("app.api.documents"),
        "enqueue_index",
        fake_enqueue,
        raising=False,
    )


# ── 3. DB limpia por test ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture(autouse=True)
async def _db():
    """Crea las tablas antes del test y descarta el engine al final.

    El ``engine.dispose()`` final libera el pool de conexiones para que el siguiente
    test (con su propio event loop) no reutilice una conexión atada al loop anterior.
    """
    import app.db.models  # noqa: F401 — puebla Base.metadata con todos los modelos
    from app.db.base import Base
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# ── 4. Cliente HTTP contra la app (ASGI, sin servidor) ────────────────────────────


@pytest_asyncio.fixture
async def client():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── 5. Sesión autenticada (org + admin + token) ───────────────────────────────────


@pytest_asyncio.fixture
async def auth(client):
    """Crea una organización con un usuario admin y devuelve sus headers + tenant_id."""
    import uuid

    from app.auth.security import hash_password
    from app.db.models.organization import Organization
    from app.db.models.user import ROLE_ADMIN, User
    from app.db.session import AsyncSessionLocal

    org_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        db.add(Organization(id=org_id, slug="test-org", name="Test Org"))
        db.add(
            User(
                id=str(uuid.uuid4()),
                email="admin@test.com",
                password_hash=hash_password("password123"),
                organization_id=org_id,
                role=ROLE_ADMIN,
                is_active=True,
            )
        )
        await db.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "tenant_id": org_id}
