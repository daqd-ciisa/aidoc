"""Conector de subida manual.

Es el conector por defecto: los archivos llegan por el endpoint de upload, así
que ``load_documents`` simplemente reemite lo que se le pasó. Existe para que el
resto del sistema trate "manual" como un conector más.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.connectors.base import RawDocument

SOURCE_MANUAL = "manual_upload"


class ManualUploadConnector:
    source = SOURCE_MANUAL

    def __init__(self, documents: list[RawDocument]) -> None:
        self._documents = documents

    def load_documents(self) -> Iterator[RawDocument]:
        yield from self._documents
