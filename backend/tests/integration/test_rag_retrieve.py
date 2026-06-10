"""Integración · recuperación híbrida (semántica + boost léxico) de rag.retrieve.

Verifica que el boost léxico rescata el chunk que contiene las palabras clave de la
consulta (caso real: datos de tablas/OCR que el coseno puro dejaría fuera del top-k).
"""
from __future__ import annotations

import pytest

from app.chat import rag
from app.ingestion.chunker import Chunk
from app.services import qdrant
from tests.fakes import FakeEmbeddings

pytestmark = pytest.mark.integration

_emb = FakeEmbeddings()


async def test_lexical_boost_ranks_keyword_chunk_first():
    texts = [
        "El total de la factura asciende a 1160 pesos.",  # contiene 'factura'
        "Generalidades del servicio y alcance del proyecto.",  # sin 'factura'
    ]
    qdrant.upsert_chunks(
        tenant_id="t", document_id="d", filename="a.txt",
        chunks=[Chunk(text=t, chunk_index=i, page=None) for i, t in enumerate(texts)],
        vectors=_emb.embed_documents(texts),
    )

    # El embedding fake es aleatorio (coseno ~0); el boost léxico (+0.4 por la palabra
    # 'factura') debe llevar ese chunk al primer lugar de forma estable.
    hits = rag.retrieve("cuánto es la factura", tenant_id="t")
    assert hits
    assert "factura" in hits[0].text.lower()
