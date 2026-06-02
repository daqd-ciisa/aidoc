"""Contrato de conector de fuentes de documentos (patrón Onyx).

Hoy solo existe la subida manual; mañana un Google Drive / S3 / SharePoint es
una nueva implementación de ``Connector`` sin tocar el pipeline de indexado.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawDocument:
    """Documento crudo que entrega un conector, antes de almacenar/indexar."""

    filename: str
    data: bytes
    content_type: str | None = None
    metadata: dict = field(default_factory=dict)


class Connector(Protocol):
    """Fuente de documentos. ``source`` identifica al conector en la metadata."""

    source: str

    def load_documents(self) -> Iterator[RawDocument]: ...
