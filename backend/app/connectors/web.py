"""Ingesta de una fuente aprobada por URL (web pública).

Descarga la URL y devuelve un item listo para ``ingest_documents``:
- Si es un PDF (QuickSpecs de HPE, guías en PDF…) → bytes tal cual, el parser
  PDF (con OCR) lo procesa en el worker.
- Si es HTML (Microsoft 365 Learn, Aruba techdocs…) → se extrae el texto legible
  con la stdlib (sin dependencias nuevas) y se entrega como .txt.

Portales JS-heavy o detrás de login (Aruba doc portal, HPE Seismic) devolverán
poco texto: para esos, la carga manual del PDF es la vía robusta.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

SOURCE_URL = "url"

# Etiquetas cuyo contenido NO es texto visible. (head NO va acá: su hijo <title>
# se captura aparte; sus otros hijos —meta/link/base— no tienen texto.)
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "article", "header", "footer", "table", "ul", "ol", "pre",
}


class _HTMLToText(HTMLParser):
    """Extrae texto legible de HTML: salta script/style y respeta saltos de bloque."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title += data
        text = data.strip()
        if text:
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        # Colapsar espacios horizontales y líneas en blanco repetidas.
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n[ \t]*", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name or parsed.netloc or "fuente"
    return name


def fetch_url(url: str) -> tuple[str, bytes, str | None]:
    """Descarga ``url`` y devuelve (nombre, bytes, content_type) para ingesta.

    Lanza si la descarga falla o si el HTML no tiene texto aprovechable."""
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "AIDOC/1.0 (+source-import)"})
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").lower()
        content = resp.content

    is_pdf = "application/pdf" in ctype or url.lower().split("?")[0].endswith(".pdf")
    if is_pdf:
        name = _slug_from_url(url)
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return name, content, "application/pdf"

    # HTML → texto.
    parser = _HTMLToText()
    parser.feed(content.decode(resp.encoding or "utf-8", errors="replace"))
    text = parser.get_text()
    if len(text) < 200:
        raise ValueError(
            "La página no devolvió texto aprovechable (¿requiere login o es "
            "JavaScript?). Subí el PDF manualmente para esta fuente."
        )

    base = _slug_from_url(url)
    title = (parser.title.strip() or base).strip()
    # Nombre legible terminado en .txt para que lo tome el parser de texto.
    safe = re.sub(r"[^\w\- .]", "_", title)[:120].strip() or "fuente"
    name = safe if safe.lower().endswith(".txt") else f"{safe}.txt"
    return name, text.encode("utf-8"), "text/plain"
