"""Unit · helpers puros de cotizaciones/propuestas."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.api.quotes import (
    FromPrecedentRequest,
    _default_valida_hasta,
    _fecha_es,
    _precedent_ids,
)
from app.quotes.proposal import commercial_terms, confidentiality_text
from app.quotes.schema import QuoteDraft
from app.quotes.summarizer import DocumentSummary, summary_to_text

pytestmark = pytest.mark.unit


# ── api.quotes ────────────────────────────────────────────────────────────────


def test_precedent_ids_merges_dedups_and_caps():
    req = FromPrecedentRequest(
        request="x",
        document_ids=["a", "b", "a", "", "c", "d", "e"],  # dup + vacío + de más
        document_id="b",  # legacy, ya presente
    )
    ids = _precedent_ids(req)
    assert ids == ["a", "b", "c", "d"]  # sin dups/vacíos, tope 4, orden preservado


def test_precedent_ids_includes_legacy_single():
    req = FromPrecedentRequest(request="x", document_id="solo")
    assert _precedent_ids(req) == ["solo"]


def test_fecha_es_formats_spanish():
    assert _fecha_es(datetime(2026, 6, 9)) == "09 de junio de 2026"


def test_default_valida_hasta_is_thirty_days_ahead():
    result = date.fromisoformat(_default_valida_hasta())
    assert result == date.today() + timedelta(days=30)


# ── summarizer ────────────────────────────────────────────────────────────────


def test_summary_to_text_includes_present_skips_none():
    s = DocumentSummary(
        categoria="servicio", cliente="ACME", servicios=["soporte", "migración"],
        objeto=None, moneda="MXN", resumen="Resumen breve.",
    )
    txt = summary_to_text(s)
    assert "Categoría: servicio" in txt
    assert "Cliente: ACME" in txt
    assert "soporte, migración" in txt
    assert "Resumen breve." in txt
    assert "Objeto:" not in txt  # era None → se omite


# ── proposal (boilerplate determinístico) ─────────────────────────────────────


def test_confidentiality_text_injects_client_name():
    txt = confidentiality_text("Globex")
    assert "Globex" in txt
    assert "De Propiedad" in txt


def test_commercial_terms_reflect_currency_and_iva():
    econ = QuoteDraft(moneda="USD", impuestos=160.0)
    txt = commercial_terms(econ, "09 de junio de 2026")
    assert "USD" in txt
    assert "IVA del 16%" in txt
    assert "09 de junio de 2026" in txt


def test_commercial_terms_without_iva():
    econ = QuoteDraft(moneda="MXN", impuestos=0.0)
    txt = commercial_terms(econ, "01 de enero de 2026")
    assert "no incluyen IVA." in txt
