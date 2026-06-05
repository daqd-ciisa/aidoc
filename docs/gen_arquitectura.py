"""Genera docs/arquitectura-aidoc.pdf reflejando el estado actual de AIDOC.

Reproduce el estilo del documento (banda navy, diagrama de componentes, tabla de
stack, flujos y decisiones). Incluye OCR, busqueda hibrida, conectores cloud,
edicion de cotizaciones y Qdrant en PCAI.

Como regenerar (reportlab vive en el contenedor backend):
    docker compose exec -T backend python - < docs/gen_arquitectura.py
    # escribe /app/arquitectura-aidoc.pdf (== backend/ en el host); luego:
    mv -f backend/arquitectura-aidoc.pdf docs/arquitectura-aidoc.pdf
"""
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

NAVY = HexColor(0x012045)
LIGHT = HexColor(0xE9EEF6)
BORDER = HexColor(0xB7C5DA)
GRAY = HexColor(0x5B6675)
SUBLIGHT = HexColor(0xC9D4E6)
ROWALT = HexColor(0xF2F5F9)

DATE = "03/06/2026"


# ── Banda de encabezado ─────────────────────────────────────────────────────
class HeaderBand(Flowable):
    def __init__(self, width, height=70):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.roundRect(0, 0, self.width, self.height, 6, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(22, self.height / 2 - 9, "AIDOC")
        c.setFont("Helvetica", 9.5)
        c.drawRightString(self.width - 22, self.height / 2 + 4, "Arquitectura tecnica")
        c.drawRightString(self.width - 22, self.height / 2 - 9, DATE)


# ── Diagrama de componentes ──────────────────────────────────────────────────
class Diagram(Flowable):
    def __init__(self, width, height=324):
        super().__init__()
        self.width = width
        self.height = height

    def _box(self, x, y, w, h, title, subs, fill=None, tcol=None, scol=GRAY):
        c = self.canv
        c.setStrokeColor(BORDER if fill is None else fill)
        c.setLineWidth(1)
        if fill is not None:
            c.setFillColor(fill)
        c.roundRect(x, y, w, h, 8, stroke=1, fill=1 if fill is not None else 0)
        cx = x + w / 2
        c.setFillColor(tcol or NAVY)
        c.setFont("Helvetica-Bold", 9.3)
        ty = y + h - 15
        c.drawCentredString(cx, ty, title)
        c.setFont("Helvetica", 7)
        c.setFillColor(scol)
        sy = ty - 11
        for s in subs:
            c.drawCentredString(cx, sy, s)
            sy -= 9

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        cw = W * 0.30
        c1, c2, c3 = W * 0.155, W * 0.5, W * 0.845

        def Y(top, h):
            return H - top - h

        # Conectores (se dibujan primero; las cajas tapan los extremos).
        c.setStrokeColor(NAVY)
        c.setLineWidth(1)
        c.line(c2, H - 44, c2, H - 70)  # Frontend -> API
        for cc in (c1, c2, c3):  # API -> fila de servicios
            c.line(c2, H - 114, cc, H - 144)
        for cc in (c1, c2, c3):  # servicios -> almacenamiento / modelos
            c.line(cc, H - 198, cc, H - 224)
        c.line(c1, H - 268, c1, H - 280)  # PostgreSQL -> MinIO
        c.line(c2, H - 268, c2, H - 280)  # Qdrant -> Redis
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(GRAY)
        c.drawCentredString(c2 + 26, H - 60, "HTTP / SSE")

        # Cajas
        self._box(c2 - W * 0.24, Y(0, 44), W * 0.48, 44, "Frontend - React + Vite",
                  ["Biblioteca - Chat", "Cotizaciones editables - dark mode"],
                  fill=NAVY, tcol=white, scol=SUBLIGHT)
        self._box(c2 - W * 0.31, Y(70, 44), W * 0.62, 44, "API - FastAPI (REST + SSE)",
                  ["async - multi-tenant (tenant_id)"], fill=NAVY, tcol=white, scol=SUBLIGHT)

        self._box(c1 - cw / 2, Y(144, 54), cw, 54, "Ingesta",
                  ["parsers PDF/DOCX/TXT/MD", "OCR (Tesseract) - chunking", "embeddings"])
        self._box(c2 - cw / 2, Y(144, 54), cw, 54, "Chat RAG",
                  ["retrieval hibrido", "(semantico + lexico)", "respuesta con citas [n]"])
        self._box(c3 - cw / 2, Y(144, 54), cw, 54, "Cotizaciones",
                  ["guiada por precedente", "edicion + export PDF"])

        self._box(c1 - cw / 2, Y(224, 44), cw, 44, "PostgreSQL", ["metadata"])
        self._box(c2 - cw / 2, Y(224, 44), cw, 44, "Qdrant",
                  ["vectores (tenant)", "en HPE PCAI"])
        self._box(c3 - cw / 2, Y(224, 100), cw, 100, "Modelos - NVIDIA NIM",
                  ["Qwen3-Embedding 0.6B (1024d)", "Qwen3-30B (chat/extraccion)", "HPE PCAI"],
                  fill=LIGHT)

        self._box(c1 - cw / 2, Y(280, 44), cw, 44, "MinIO / S3", ["archivos originales"])
        self._box(c2 - cw / 2, Y(280, 44), cw, 44, "Redis + ARQ", ["worker async"])


# ── Documento ────────────────────────────────────────────────────────────────
def build(path: str) -> None:
    doc = BaseDocTemplate(
        path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
    )
    fw = doc.width
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame])])

    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                        textColor=NAVY, spaceBefore=10, spaceAfter=6)
    sub = ParagraphStyle("sub", fontName="Helvetica-Bold", fontSize=9.5,
                         textColor=NAVY, spaceBefore=6, spaceAfter=2)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                          textColor=HexColor(0x222222), leading=14, spaceAfter=4)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=12,
                            bulletIndent=2, spaceAfter=3)

    story = [HeaderBand(fw), Spacer(1, 16)]

    story += [Paragraph("Resumen", h2), Paragraph(
        "AIDOC es una plataforma de analisis documental conversacional (RAG). El usuario "
        "sube una biblioteca de documentos (subida manual o desde Google Drive / OneDrive) "
        "que se indexan en una base vectorial; luego puede chatear sobre ellos con "
        "respuestas citadas y generar cotizaciones guiadas por cotizaciones existentes, "
        "editables antes de exportarlas. Aplicacion standalone, single-tenant hoy y "
        "disenada para multi-tenant sin migracion.", body)]

    story += [Paragraph("Diagrama de componentes", h2), Diagram(fw), Spacer(1, 14)]

    story += [Paragraph("Stack tecnologico", h2)]
    rows = [
        ["Capa", "Tecnologia"],
        ["Frontend", "React 18 + Vite + TypeScript + TailwindCSS (SPA, SSE, dark mode)"],
        ["Backend / API", "Python 3.11 + FastAPI (async), SQLAlchemy 2 + Alembic"],
        ["Base de datos", "PostgreSQL (metadata: documentos, chats, cotizaciones, organizacion)"],
        ["Vector store", "Qdrant en HPE PCAI (embeddings filtrados por tenant_id; sin API key)"],
        ["Almacenamiento", "MinIO / S3 (archivos originales)"],
        ["Cola / worker", "Redis + ARQ (indexado asincrono en segundo plano)"],
        ["OCR", "Tesseract (pytesseract + Pillow) sobre paginas-imagen, lang spa+eng"],
        ["Busqueda", "Hibrida: similitud coseno + boost lexico por palabras clave"],
        ["Conectores", "Subida manual - Google Drive (GIS + Picker) - OneDrive (MSAL + Graph)"],
        ["Modelos (IA)", "NVIDIA NIM sobre HPE PCAI - Qwen3-Embedding-0.6B + Qwen3-30B"],
        ["Generacion PDF", "reportlab (plantilla de cotizacion / este documento)"],
    ]
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.7,
                          textColor=HexColor(0x222222), leading=11)
    cap = ParagraphStyle("cap", fontName="Helvetica-Bold", fontSize=8.7,
                         textColor=NAVY, leading=11)
    data = [[Paragraph(rows[0][0], ParagraphStyle("hcap", parent=cap, textColor=white)),
             Paragraph(rows[0][1], ParagraphStyle("hcap2", parent=cell, textColor=white,
                                                  fontName="Helvetica-Bold"))]]
    for r in rows[1:]:
        data.append([Paragraph(r[0], cap), Paragraph(r[1], cell)])
    tbl = Table(data, colWidths=[fw * 0.26, fw * 0.74])
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            ts.append(("BACKGROUND", (0, i), (-1, i), ROWALT))
    tbl.setStyle(TableStyle(ts))
    story += [tbl, Spacer(1, 12)]

    story += [Paragraph("Flujos principales", h2)]
    story += [Paragraph("1. Ingesta e indexado", sub), Paragraph(
        "Subida manual o conectores (Google Drive / OneDrive) -> guardado en MinIO -> "
        "encolado en Redis/ARQ -> el worker extrae texto (PDF/DOCX/TXT/MD), aplica OCR "
        "(Tesseract) a las paginas que son imagen (tablas o propuestas escaneadas), hace "
        "chunking, embebe con NVIDIA NIM y hace upsert en Qdrant. "
        "Estados: pending -> processing -> indexed/failed.", body)]
    story += [Paragraph("2. Chat RAG con citas", sub), Paragraph(
        "La pregunta se embebe y se recuperan los fragmentos mas relevantes en Qdrant "
        "(filtrado por tenant y opcionalmente por documentos) con busqueda hibrida: "
        "similitud semantica mas un re-ranking lexico por palabras clave que rescata datos "
        "de tablas/OCR. Se arma el contexto y el LLM responde por streaming (SSE) citando "
        "las fuentes [n].", body)]
    story += [Paragraph("3. Cotizacion guiada por precedente", sub), Paragraph(
        "El usuario describe la cotizacion; el sistema rankea por documento las cotizaciones "
        "mas parecidas y pide confirmacion; con el precedente elegido (documento completo) el "
        "LLM genera el borrador reutilizando items y precios. El borrador es editable "
        "(cliente, items, impuestos con IVA 16% automatico, condiciones) y se exporta a PDF "
        "con plantilla generica.", body)]

    story += [Paragraph("Decisiones de arquitectura", h2)]
    decisiones = [
        "Qdrant en HPE PCAI (compartido, desplegado con apiKey:false); en desarrollo se uso "
        "un contenedor local y luego se apunto a PCAI sin migracion.",
        "OCR selectivo: solo se OCR-ean paginas con poco texto e imagenes, sin penalizar el "
        "resto del documento.",
        "Busqueda hibrida (semantica + lexica) para no perder datos en tablas/escaneos que la "
        "similitud pura deja fuera del top-k.",
        "Conectores cloud con patron cliente-amigable: tokens efimeros en el navegador "
        "(Google Identity Services / MSAL), sin almacenar refresh tokens.",
        "Single-tenant hoy, multi-tenant sin migracion: todo modelo y cada punto Qdrant "
        "llevan tenant_id.",
        "Subida manual primero; conectores externos via la interfaz Connector.",
        "Cotizaciones guiadas por precedente y editables tras la generacion, en vez de partir "
        "de cero.",
        "VERIFY_SSL=false hacia PCAI por certificados self-signed; credenciales por variables "
        "de entorno.",
    ]
    for d in decisiones:
        story.append(Paragraph(d, bullet, bulletText="•"))

    doc.build(story)
    print("OK ->", path)


if __name__ == "__main__":
    build("/app/arquitectura-aidoc.pdf")
