"""Parser de PDF vía PyMuPDF (fitz), texto por página + OCR de fallback.

Si una página tiene poco texto extraíble pero contiene imágenes (típico de
tablas/propuestas económicas embebidas como imagen), se OCR-ea y se anexa el
texto reconocido."""
from __future__ import annotations

import fitz

from app.ingestion.ocr import ocr_page_text, should_ocr
from app.ingestion.parsers.base import ParsedPage


def parse(path: str) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if should_ocr(text, page):
                ocr = ocr_page_text(page)
                if ocr:
                    text = f"{text}\n{ocr}".strip() if text else ocr
            if text:
                pages.append(ParsedPage(text=text, page=i))
    return pages
