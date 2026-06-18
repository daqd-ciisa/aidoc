"""Schemas del reporte de validación (separados para evitar imports circulares).

``ProposalDraft`` incrusta un ``ValidationReport`` (validación automática al
crear), y ``validation.py`` los produce — por eso viven acá, sin depender de
ninguno de los dos.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ClaimVerdict(BaseModel):
    afirmacion: str
    estado: str  # respaldado | contradice | sin_respaldo
    fuente: str | None = None      # nombre/etiqueta de la fuente que la respalda
    fuente_url: str | None = None  # URL aprobada (si vino de una fuente en vivo)
    snippet: str | None = None
    motivo: str | None = None
    # Modo B (corrección asistida): texto VERBATIM de la propuesta del que salió la
    # afirmación (para reemplazar), y la corrección sugerida según la fuente (solo
    # cuando estado="contradice").
    origen: str | None = None
    correccion: str | None = None


class ValidationReport(BaseModel):
    corpus_vacio: bool = False  # no hay URLs aprobadas ni documentos reference
    afirmaciones: list[ClaimVerdict] = Field(default_factory=list)
    respaldadas: int = 0
    contradichas: int = 0
    sin_respaldo: int = 0
