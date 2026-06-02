"""Registry de parsers por extensión."""
from __future__ import annotations

from collections.abc import Callable

from app.ingestion.parsers import docx as docx_parser
from app.ingestion.parsers import pdf as pdf_parser
from app.ingestion.parsers import text as text_parser
from app.ingestion.parsers.base import ParsedPage

ParseFn = Callable[[str], list[ParsedPage]]

_REGISTRY: dict[str, ParseFn] = {
    ".pdf": pdf_parser.parse,
    ".docx": docx_parser.parse,
    ".txt": text_parser.parse,
    ".md": text_parser.parse,
}

SUPPORTED_EXTENSIONS = frozenset(_REGISTRY)


def get_parser(extension: str) -> ParseFn | None:
    return _REGISTRY.get(extension.lower())
