"""Integración · pipeline de indexado (parse → chunk → embed → upsert + resumen).

Ejercita ``pipeline.run_indexing`` de punta a punta contra el Qdrant en memoria y el
storage en dict (fixtures del conftest), con embeddings/LLM falseados. No pasa por
HTTP ni por el worker ARQ: prueba el slice de ingesta aislado.
"""
from __future__ import annotations

import pytest

from app.chat import rag
from app.ingestion import pipeline
from app.services import qdrant, storage

pytestmark = pytest.mark.integration

DOC = (
    "Cotización para el cliente ACME.\n"
    "Servicio de soporte técnico mensual. Total: 1160 MXN.\n"
)


async def test_run_indexing_creates_chunks_and_summary_point():
    doc_id, tenant = "doc-int-1", "tenant-int"
    key = f"{tenant}/{doc_id}.txt"
    storage.upload_bytes(key, DOC.encode(), "text/plain")

    n = pipeline.run_indexing(
        document_id=doc_id,
        tenant_id=tenant,
        storage_key=key,
        filename="acme.txt",
        extension=".txt",
    )
    assert n >= 1

    # Los chunks quedaron en Qdrant, aislados por documento.
    chunks = qdrant.get_document_chunks(tenant_id=tenant, document_id=doc_id)
    assert len(chunks) == n
    assert all(c["document_id"] == doc_id for c in chunks)

    # Y se generó el punto kind="summary" → el doc es hallable como precedente.
    precedents = rag.rank_documents(query="soporte técnico", tenant_id=tenant)
    assert any(p["document_id"] == doc_id for p in precedents)


async def test_reindex_is_idempotent_on_vectors():
    doc_id, tenant = "doc-int-2", "tenant-int"
    key = f"{tenant}/{doc_id}.txt"
    storage.upload_bytes(key, DOC.encode(), "text/plain")

    n1 = pipeline.run_indexing(
        document_id=doc_id, tenant_id=tenant, storage_key=key,
        filename="acme.txt", extension=".txt",
    )
    # Reindexar el mismo doc no duplica chunks (borra los previos antes de subir).
    n2 = pipeline.run_indexing(
        document_id=doc_id, tenant_id=tenant, storage_key=key,
        filename="acme.txt", extension=".txt",
    )
    assert n1 == n2
    assert len(qdrant.get_document_chunks(tenant_id=tenant, document_id=doc_id)) == n2
