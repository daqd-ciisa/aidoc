"""Los tests unitarios prueban lógica PURA → no necesitan DB, Qdrant ni parches.

Acá se sobreescriben (por nombre) los fixtures autouse del conftest padre con
versiones no-op, para que los unitarios queden rápidos y sin I/O.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _patch_services():  # type: ignore[override]
    yield


@pytest.fixture(autouse=True)
def _db():  # type: ignore[override]
    yield
