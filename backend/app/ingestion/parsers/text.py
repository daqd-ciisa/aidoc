"""Parser de texto plano (.txt / .md)."""
from __future__ import annotations

from pathlib import Path

from app.ingestion.parsers.base import ParsedPage


def parse(path: str) -> list[ParsedPage]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return [ParsedPage(text=text, page=None)] if text.strip() else []
