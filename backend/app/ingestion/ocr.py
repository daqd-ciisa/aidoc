"""OCR de páginas PDF cuyo contenido viene como imagen (tablas, escaneos).

Fallback: el parser de texto (PyMuPDF) no lee imágenes, así que tablas de
precios/diagramas embebidos como imagen quedan invisibles. Acá renderizamos la
página y la pasamos por Tesseract para recuperar ese texto."""
from __future__ import annotations

import io
import logging

logger = logging.getLogger("aidoc.ocr")

# Páginas con menos texto que esto Y con al menos una imagen → candidatas a OCR.
TEXT_THRESHOLD = 1200
_OCR_LANG = "spa+eng"
_OCR_DPI = 200


def should_ocr(text: str, page) -> bool:
    """¿Conviene OCR-ear esta página? (poco texto extraíble + tiene imágenes)."""
    if len(text) >= TEXT_THRESHOLD:
        return False
    try:
        return len(page.get_images()) > 0
    except Exception:  # noqa: BLE001
        return False


def ocr_page_text(page) -> str:
    """Renderiza la página y devuelve el texto reconocido por OCR.

    Devuelve "" si el OCR no está disponible o falla (degradación segura)."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:  # noqa: BLE001
        logger.warning("OCR no disponible: falta pytesseract/Pillow o Tesseract.")
        return ""
    try:
        pix = page.get_pixmap(dpi=_OCR_DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, lang=_OCR_LANG).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR falló en la página: %s", exc)
        return ""
