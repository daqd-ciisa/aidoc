"""Integración · servicio Qdrant: aislamiento por tenant y filtrado por kind.

Contra el cliente Qdrant en memoria (fixture del conftest). Verifica las garantías
de las que dependen el chat y la búsqueda de precedentes.
"""
from __future__ import annotations

import pytest

from app.ingestion.chunker import Chunk
from app.services import qdrant
from tests.fakes import FakeEmbeddings

pytestmark = pytest.mark.integration

_emb = FakeEmbeddings()


def _chunks(texts):
    return [Chunk(text=t, chunk_index=i, page=None) for i, t in enumerate(texts)]


async def test_search_is_isolated_by_tenant():
    qdrant.upsert_chunks(
        tenant_id="t1", document_id="d1", filename="a.txt",
        chunks=_chunks(["soporte técnico", "migración"]),
        vectors=_emb.embed_documents(["soporte técnico", "migración"]),
    )
    qdrant.upsert_chunks(
        tenant_id="t2", document_id="d2", filename="b.txt",
        chunks=_chunks(["otra cosa"]), vectors=_emb.embed_documents(["otra cosa"]),
    )
    q = _emb.embed_query("soporte")

    hits_t1 = qdrant.search(query_vector=q, tenant_id="t1", top_k=10)
    assert hits_t1 and all(h["document_id"] == "d1" for h in hits_t1)

    hits_t2 = qdrant.search(query_vector=q, tenant_id="t2", top_k=10)
    assert all(h["document_id"] == "d2" for h in hits_t2)


async def test_search_excludes_summary_by_default_and_filters_by_kind():
    qdrant.upsert_chunks(
        tenant_id="t", document_id="d", filename="a.txt",
        chunks=_chunks(["contenido del documento"]),
        vectors=_emb.embed_documents(["contenido del documento"]),
    )
    qdrant.upsert_summary(
        tenant_id="t", document_id="d", filename="a.txt",
        vector=_emb.embed_query("resumen"), summary_text="resumen de alto nivel",
        summary={"categoria": "servicio"},
    )
    q = _emb.embed_query("algo")

    # Por defecto la búsqueda de CONTENIDO excluye el punto de resumen.
    default_hits = qdrant.search(query_vector=q, tenant_id="t", top_k=10)
    assert default_hits
    assert all(h.get("summary") is None for h in default_hits)

    # kind="summary" devuelve SOLO el resumen.
    sum_hits = qdrant.search(query_vector=q, tenant_id="t", top_k=10, kind="summary")
    assert sum_hits and all(h.get("summary") is not None for h in sum_hits)


async def test_search_filters_by_doc_type():
    qdrant.upsert_chunks(
        tenant_id="t", document_id="doc-normal", filename="propuesta.docx",
        chunks=_chunks(["servicio de soporte"]),
        vectors=_emb.embed_documents(["servicio de soporte"]),
    )
    qdrant.upsert_chunks(
        tenant_id="t", document_id="doc-cat", filename="catalogo.xlsx",
        chunks=_chunks(["SRV26014 | IMPLEMENTACIÓN DE CÓMPUTO | 300"]),
        vectors=_emb.embed_documents(["SRV26014 | IMPLEMENTACIÓN DE CÓMPUTO | 300"]),
        doc_type="catalog",
    )
    q = _emb.embed_query("cómputo")

    # doc_type="catalog" devuelve SOLO los puntos del catálogo.
    cat_hits = qdrant.search(query_vector=q, tenant_id="t", top_k=10, doc_type="catalog")
    assert cat_hits and all(h["document_id"] == "doc-cat" for h in cat_hits)

    # Sin filtro, la búsqueda de contenido (chat) sigue viendo TODO.
    all_hits = qdrant.search(query_vector=q, tenant_id="t", top_k=10)
    assert {h["document_id"] for h in all_hits} == {"doc-normal", "doc-cat"}


async def test_get_document_chunks_orders_and_excludes_summary():
    texts = ["chunk-0", "chunk-1", "chunk-2"]
    qdrant.upsert_chunks(
        tenant_id="t", document_id="d", filename="a.txt",
        chunks=_chunks(texts), vectors=_emb.embed_documents(texts),
    )
    qdrant.upsert_summary(
        tenant_id="t", document_id="d", filename="a.txt",
        vector=_emb.embed_query("s"), summary_text="s", summary={},
    )
    chunks = qdrant.get_document_chunks(tenant_id="t", document_id="d")
    assert [c["chunk_index"] for c in chunks] == [0, 1, 2]  # ordenado, sin el resumen
