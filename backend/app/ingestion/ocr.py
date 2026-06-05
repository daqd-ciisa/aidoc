"""OCR de contenido embebido como imagen (tablas de precios, escaneos, diagramas).

Fallback: ni PyMuPDF (PDF) ni python-docx (DOCX) leen texto dentro de imágenes,
así que tablas de precios/propuestas económicas embebidas como imagen quedan
invisibles. Acá las renderizamos/abrimos y las pasamos por Tesseract."""
from __future__ import annotations

import io
import logging

logger = logging.getLogger("aidoc.ocr")

# Páginas PDF con menos texto que esto Y con al menos una imagen → candidatas a OCR.
TEXT_THRESHOLD = 1200
# Imágenes embebidas más chicas que esto (px en ambos lados) se asumen
# logos/iconos decorativos y NO se OCR-ean (evita ruido y trabajo inútil).
MIN_IMAGE_PX = 200
_OCR_LANG = "spa+eng"
_OCR_DPI = 200


def should_ocr(text: str, page) -> bool:
    """¿Conviene OCR-ear esta página PDF? (poco texto extraíble + tiene imágenes)."""
    if len(text) >= TEXT_THRESHOLD:
        return False
    try:
        return len(page.get_images()) > 0
    except Exception:  # noqa: BLE001
        return False


def _ocr_pil_image(img) -> str:
    """Corre Tesseract sobre una imagen PIL ya abierta. "" si falla/no disponible."""
    try:
        import pytesseract
    except Exception:  # noqa: BLE001
        logger.warning("OCR no disponible: falta pytesseract o Tesseract.")
        return ""
    try:
        return pytesseract.image_to_string(img, lang=_OCR_LANG).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR falló: %s", exc)
        return ""


def ocr_page_text(page) -> str:
    """Renderiza una página PDF (PyMuPDF) y devuelve el texto reconocido por OCR."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        logger.warning("OCR no disponible: falta Pillow.")
        return ""
    try:
        pix = page.get_pixmap(dpi=_OCR_DPI)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR falló al renderizar la página: %s", exc)
        return ""
    return _ocr_pil_image(img)


def ocr_image_bytes(blob: bytes) -> str:
    """OCR de una imagen embebida (p.ej. la tabla de precios dentro de un .docx).

    Devuelve "" si la imagen es muy chica (logo/icono), si no se puede abrir, o si
    el OCR no está disponible/falla (degradación segura)."""
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001
        logger.warning("OCR no disponible: falta Pillow.")
        return ""
    try:
        img = Image.open(io.BytesIO(blob))
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR no pudo abrir la imagen embebida: %s", exc)
        return ""
    width, height = img.size
    if width < MIN_IMAGE_PX or height < MIN_IMAGE_PX:
        return ""  # logo/icono decorativo
    return _ocr_pil_image(img)
