"""Unit · parseo tolerante de JSON y limpieza de etiquetas de precedente."""
from __future__ import annotations

import pytest

from app.quotes.extractor import _parse_json, strip_precedent_labels

pytestmark = pytest.mark.unit


def test_parse_plain_json():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_strips_json_fence():
    raw = '```json\n{"a": 1, "b": "x"}\n```'
    assert _parse_json(raw) == {"a": 1, "b": "x"}


def test_parse_strips_bare_fence():
    assert _parse_json('```\n{"ok": true}\n```') == {"ok": True}


def test_parse_recovers_object_from_surrounding_text():
    raw = 'Claro, aquí tenés:\n{"total": 100}\nEspero que sirva.'
    assert _parse_json(raw) == {"total": 100}


def test_parse_invalid_raises():
    with pytest.raises(Exception):
        _parse_json("esto no es json")


def test_strip_named_precedent_label():
    out = strip_precedent_labels("Basado en [PRECEDENTE 1: cotizacion_acme.pdf] y más.")
    assert "[PRECEDENTE" not in out
    assert "«cotizacion_acme.pdf»" in out


def test_strip_plain_precedent_label():
    out = strip_precedent_labels("Ver [PRECEDENTE 2] para detalles.")
    assert "[PRECEDENTE" not in out
    assert "el precedente principal" in out


def test_strip_handles_none_and_clean_text():
    assert strip_precedent_labels(None) is None
    assert strip_precedent_labels("texto limpio") == "texto limpio"
