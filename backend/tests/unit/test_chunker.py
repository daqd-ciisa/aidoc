"""Unit · chunking de páginas (índice global secuencial + página preservada)."""
from __future__ import annotations

import pytest

from app.ingestion.chunker import chunk_pages
from app.ingestion.parsers.base import ParsedPage

pytestmark = pytest.mark.unit


def test_empty_pages_yield_no_chunks():
    assert chunk_pages([]) == []
    assert chunk_pages([ParsedPage(text="", page=1)]) == []


def test_single_page_produces_indexed_chunk():
    chunks = chunk_pages([ParsedPage(text="Hola mundo", page=3)])
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page == 3
    assert chunks[0].text == "Hola mundo"


def test_chunk_index_is_global_across_pages():
    # Texto largo (> CHUNK_SIZE) en dos páginas → varios chunks con índice continuo.
    long_text = "palabra " * 600  # ~4800 chars, fuerza múltiples chunks
    chunks = chunk_pages(
        [ParsedPage(text=long_text, page=1), ParsedPage(text=long_text, page=2)]
    )
    assert len(chunks) > 2
    # Los índices son globales, secuenciales y sin huecos.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # Las páginas se preservan y aparecen ambas.
    assert {c.page for c in chunks} == {1, 2}
