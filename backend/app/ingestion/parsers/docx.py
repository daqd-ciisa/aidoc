"""Parser de DOCX vía python-docx: párrafos + tablas + OCR de imágenes embebidas.

``python-docx`` solo expone texto de párrafos: NO lee tablas ni el texto dentro de
imágenes. En las propuestas reales de CiiSA la tabla de precios (propuesta
económica) viene como tabla de Word o, más a menudo, como **imagen** embebida —
ambos casos quedaban invisibles antes. Acá extraemos:
  - párrafos y tablas en orden de lectura, y
  - el texto OCR de las imágenes embebidas suficientemente grandes."""
from __future__ import annotations

import logging

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.ingestion.ocr import ocr_image_bytes
from app.ingestion.parsers.base import ParsedPage

logger = logging.getLogger("aidoc.parsers.docx")

_TAG_P = qn("w:p")
_TAG_TBL = qn("w:tbl")

# Solo OCR-eamos imágenes ráster (las que PIL/Tesseract pueden abrir). Word también
# embebe vectoriales (svg/emf/wmf) para logos e iconos —de los que además guarda un
# PNG de respaldo—; intentarlos solo genera ruido en el log.
_RASTER_IMAGE_TYPES = frozenset({
    "image/png", "image/jpeg", "image/jpg", "image/bmp",
    "image/tiff", "image/gif", "image/webp",
})


def _iter_block_items(doc):
    """Itera párrafos y tablas del cuerpo del documento en orden de lectura."""
    for child in doc.element.body.iterchildren():
        if child.tag == _TAG_P:
            yield Paragraph(child, doc)
        elif child.tag == _TAG_TBL:
            yield Table(child, doc)


def _table_text(table: Table) -> str:
    """Renderiza una tabla como filas ``celda | celda | …`` (filas vacías fuera)."""
    rows = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _embedded_images_text(doc) -> str:
    """OCR de las imágenes embebidas (la tabla de precios como imagen, etc.)."""
    try:
        related = doc.part.related_parts.values()
    except Exception:  # noqa: BLE001
        return ""
    chunks: list[str] = []
    seen: set[tuple[int, bytes]] = set()
    for part in related:
        if (getattr(part, "content_type", "") or "").lower() not in _RASTER_IMAGE_TYPES:
            continue
        try:
            blob = part.blob
        except Exception:  # noqa: BLE001
            continue
        key = (len(blob), blob[:16])  # evita re-OCR de imágenes repetidas (headers)
        if key in seen:
            continue
        seen.add(key)
        text = ocr_image_bytes(blob)
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)


def parse(path: str) -> list[ParsedPage]:
    doc = DocxDocument(path)
    parts: list[str] = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                parts.append(text)
        else:  # Table
            text = _table_text(block)
            if text:
                parts.append(text)
    image_text = _embedded_images_text(doc)
    if image_text:
        parts.append(image_text)
    full = "\n".join(parts).strip()
    return [ParsedPage(text=full, page=None)] if full else []
