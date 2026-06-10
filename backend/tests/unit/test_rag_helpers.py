"""Unit · helpers puros de RAG (normalización, términos, contexto, citas)."""
from __future__ import annotations

import pytest

from app.chat.rag import (
    RetrievedChunk,
    _normalize,
    _query_terms,
    build_citations,
    build_context,
)

pytestmark = pytest.mark.unit


def test_normalize_strips_accents_and_lowercases():
    assert _normalize("Cotización ÁÉÍ") == "cotizacion aei"


def test_query_terms_drops_stopwords_and_short_tokens():
    terms = _query_terms("¿Cuál es el total de la factura?")
    # "cual" es stopword; "es"/"el"/"la" miden <3 → fuera. Quedan los significativos.
    assert "factura" in terms
    assert "total" in terms
    assert "cual" not in terms
    assert "el" not in terms


def test_query_terms_keeps_three_letter_keywords():
    # 'iva' tiene 3 chars y no es stopword → debe conservarse.
    assert "iva" in _query_terms("monto de IVA")


def _chunk(i, text, page=None):
    return RetrievedChunk(
        document_id=f"doc-{i}", filename=f"f{i}.pdf", page=page,
        chunk_index=i, text=text, score=0.9 - i * 0.1,
    )


def test_build_context_uses_numbered_markers_and_page():
    ctx = build_context([_chunk(1, "alpha", page=5), _chunk(2, "beta")])
    assert "[1] (f1.pdf p.5)" in ctx
    assert "[2] (f2.pdf)" in ctx
    assert "alpha" in ctx and "beta" in ctx


def test_build_citations_shape_and_snippet_truncation():
    long_text = "x" * 500
    cites = build_citations([_chunk(1, long_text, page=2)])
    assert len(cites) == 1
    c = cites[0]
    assert c["ref"] == 1
    assert c["document_id"] == "doc-1"
    assert c["page"] == 2
    assert len(c["snippet"]) == 300  # recortado
    assert isinstance(c["score"], float)
