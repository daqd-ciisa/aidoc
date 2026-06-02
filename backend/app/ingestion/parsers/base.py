"""Contrato de parser de documentos."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ParsedPage:
    """Un fragmento de texto extraído de una página.

    ``page`` es 1-based; ``None`` para formatos sin paginación (docx, txt).
    """

    text: str
    page: int | None = None


class Parser(Protocol):
    def __call__(self, path: str) -> list[ParsedPage]: ...
