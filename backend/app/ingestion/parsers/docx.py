"""Parser de DOCX vía python-docx (sin paginación)."""
from __future__ import annotations

from docx import Document as DocxDocument

from app.ingestion.parsers.base import ParsedPage


def parse(path: str) -> list[ParsedPage]:
    doc = DocxDocument(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [ParsedPage(text=text, page=None)] if text.strip() else []
