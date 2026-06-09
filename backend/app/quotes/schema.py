"""Esquema de la cotización de servicios (borrador extraído de documentos)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class QuoteItem(BaseModel):
    servicio: str
    descripcion: str | None = None
    cantidad: float | None = None
    precio_unitario: float | None = None
    importe: float | None = None


class QuoteDraft(BaseModel):
    """Cotización estructurada. Campos no hallados en los documentos → None,
    y listados en ``no_encontrado``."""

    cliente: str | None = None
    moneda: str | None = None
    items: list[QuoteItem] = Field(default_factory=list)
    subtotal: float | None = None
    impuestos: float | None = None
    total: float | None = None
    vigencia: str | None = None
    # Fecha (ISO yyyy-mm-dd) hasta la que la cotización es válida. La fija el backend al
    # generar (por defecto 30 días) y es editable; sirve para filtrar vigentes/vencidas.
    valida_hasta: str | None = None
    condiciones: str | None = None
    notas: str | None = None
    no_encontrado: list[str] = Field(default_factory=list)
