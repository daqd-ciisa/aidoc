"""Unit · catálogo en cotizaciones: armado de prompts y degradación segura."""
from __future__ import annotations

import pytest

from app.quotes import catalog as catalog_mod
from app.quotes.extractor import CATALOG_RULES, _with_catalog

pytestmark = pytest.mark.unit


def test_with_catalog_none_leaves_prompt_untouched():
    system, body = _with_catalog("SYSTEM", "BODY", None)
    assert system == "SYSTEM"
    assert body == "BODY"
    system, body = _with_catalog("SYSTEM", "BODY", "")
    assert (system, body) == ("SYSTEM", "BODY")


def test_with_catalog_appends_rules_and_block():
    block = "[CATÁLOGO DE SERVICIOS]\n(catalogo.xlsx)\nSRV26014 | CÓMPUTO | 300"
    system, body = _with_catalog("SYSTEM", "BODY", block)
    assert system == "SYSTEM" + CATALOG_RULES
    assert body.startswith("BODY")
    assert block in body


def test_catalog_context_degrades_to_empty_on_search_failure(monkeypatch):
    def boom(*_a, **_kw):
        raise RuntimeError("qdrant caído")

    monkeypatch.setattr(catalog_mod.rag, "retrieve", boom)
    assert catalog_mod.catalog_context("t", "pedido") == ""
