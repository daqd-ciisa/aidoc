"""Render de una cotización a PDF con una plantilla genérica y prolija.

Usa reportlab/Platypus (sin dependencias de sistema). El PDF es el documento
limpio para el cliente — NO incluye metadata interna (precedente usado, etc.)."""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.quotes.schema import QuoteDraft

_LOGO_WHITE = os.path.join(os.path.dirname(__file__), "assets", "ciisa_logo_white.png")
_CONTACT = "ciisa.com   ·   México - Colombia   ·   soporte@ciisa.com   ·   (81) 1257-8000"

# Paleta alineada a CIISA: navy dominante (#012045) + neutros fríos.
BRAND = colors.HexColor("#012045")
BRAND_LIGHT = colors.HexColor("#eaeef4")
INK = colors.HexColor("#1c1917")
MUTED = colors.HexColor("#6b7280")
BORDER = colors.HexColor("#e2e7ef")
ROW_ALT = colors.HexColor("#f6f8fb")

_PS = ParagraphStyle


def _money(v: float | None, cur: str | None) -> str:
    if v is None:
        return "—"
    s = f"{v:,.2f}"
    return f"{cur} {s}" if cur else s


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": _PS("h1", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white),
        "hsub": _PS("hsub", fontName="Helvetica", fontSize=9.5, textColor=colors.white),
        "label": _PS(
            "label", fontName="Helvetica-Bold", fontSize=7.5, textColor=MUTED
        ),
        "value": _PS("value", fontName="Helvetica", fontSize=10.5, textColor=INK),
        "svc": _PS("svc", fontName="Helvetica-Bold", fontSize=9.5, textColor=INK),
        "desc": _PS(
            "desc", fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10
        ),
        "cellr": _PS(
            "cellr", fontName="Helvetica", fontSize=9.5, textColor=INK, alignment=TA_RIGHT
        ),
        "th": _PS("th", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white),
        "thr": _PS(
            "thr",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            alignment=TA_RIGHT,
        ),
        "sect": _PS(
            "sect", fontName="Helvetica-Bold", fontSize=9, textColor=BRAND, spaceAfter=3
        ),
        "body": _PS("body", fontName="Helvetica", fontSize=9, textColor=INK, leading=13),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    w, _ = A4
    canvas.drawString(2 * cm, 1.1 * cm, "Generado con AIDOC")
    canvas.drawRightString(w - 2 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.line(2 * cm, 1.45 * cm, w - 2 * cm, 1.45 * cm)
    canvas.restoreState()


def render_quote_pdf(
    draft: QuoteDraft,
    title: str,
    quote_number: str | None = None,
    company_name: str = "AIDOC",
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        title=title or "Cotización",
    )
    s = _styles()
    cur = draft.moneda
    usable = A4[0] - 4 * cm  # ancho útil (≈17cm)
    story: list = []

    # ── Encabezado (banda de marca) ──
    fecha = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    right_lines = [company_name]
    if quote_number:
        right_lines.append(f"N° {quote_number}")
    right_lines.append(fecha)
    header = Table(
        [
            [
                Paragraph("COTIZACIÓN", s["h1"]),
                Paragraph("<br/>".join(right_lines), s["hsub"]),
            ]
        ],
        colWidths=[usable * 0.6, usable * 0.4],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.append(header)
    story.append(Spacer(1, 16))

    # ── Datos generales ──
    def _meta_cell(label: str, value: str | None):
        return [Paragraph(label, s["label"]), Paragraph(value or "—", s["value"])]

    meta = Table(
        [
            [
                _meta_cell("CLIENTE", draft.cliente),
                _meta_cell("MONEDA", draft.moneda),
                _meta_cell("VIGENCIA", draft.vigencia),
                _meta_cell("FECHA", fecha),
            ]
        ],
        colWidths=[usable * 0.4, usable * 0.2, usable * 0.2, usable * 0.2],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 18))

    # ── Tabla de ítems ──
    data: list = [
        [
            Paragraph("SERVICIO", s["th"]),
            Paragraph("CANT.", s["thr"]),
            Paragraph("P. UNIT.", s["thr"]),
            Paragraph("IMPORTE", s["thr"]),
        ]
    ]
    for it in draft.items:
        svc = Paragraph(it.servicio or "—", s["svc"])
        if it.descripcion:
            svc = [svc, Paragraph(it.descripcion, s["desc"])]
        cant = "—" if it.cantidad is None else f"{it.cantidad:g}"
        data.append(
            [
                svc,
                Paragraph(cant, s["cellr"]),
                Paragraph(_money(it.precio_unitario, None), s["cellr"]),
                Paragraph(_money(it.importe, None), s["cellr"]),
            ]
        )
    if not draft.items:
        data.append([Paragraph("Sin ítems.", s["desc"]), "", "", ""])

    items = Table(
        data,
        colWidths=[usable * 0.52, usable * 0.13, usable * 0.175, usable * 0.175],
        repeatRows=1,
    )
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    story.append(items)
    story.append(Spacer(1, 12))

    # ── Totales (alineados a la derecha) ──
    totals = Table(
        [
            ["Subtotal", _money(draft.subtotal, cur)],
            ["Impuestos", _money(draft.impuestos, cur)],
            ["TOTAL", _money(draft.total, cur)],
        ],
        colWidths=[usable * 0.18, usable * 0.22],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 1), 9.5),
                ("FONTSIZE", (0, 2), (-1, 2), 12),
                ("TEXTCOLOR", (0, 0), (0, 1), MUTED),
                ("TEXTCOLOR", (0, 2), (-1, 2), BRAND),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, 2), (-1, 2), 1, BRAND),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(totals)

    # ── Condiciones / notas ──
    if draft.condiciones:
        story.append(Spacer(1, 22))
        story.append(Paragraph("CONDICIONES", s["sect"]))
        story.append(HRFlowable(width="100%", color=BORDER, thickness=0.5, spaceAfter=6))
        story.append(Paragraph(draft.condiciones, s["body"]))

    if draft.notas:
        story.append(Spacer(1, 14))
        story.append(Paragraph("NOTAS", s["sect"]))
        story.append(HRFlowable(width="100%", color=BORDER, thickness=0.5, spaceAfter=6))
        story.append(Paragraph(draft.notas, s["body"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ── Propuesta COMPLETA (multi-sección, estilo CiiSA) ──────────────────────────────


def _esc(text: str) -> str:
    """Escapa los caracteres que reportlab interpreta como markup."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _content_flowables(text: str, s: dict) -> list:
    """Convierte texto plano (con viñetas "- " y saltos de línea) en flowables."""
    out: list = []
    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line[:2] in ("- ", "• ", "* "):
            out.append(Paragraph(_esc(line[2:].strip()), s["bullet"], bulletText="•"))
        else:
            out.append(Paragraph(_esc(line), s["body"]))
    return out


def _econ_flowables(draft: QuoteDraft, s: dict, usable: float) -> list:
    """Tabla de ítems + totales de la cotización económica (reutilizable)."""
    cur = draft.moneda
    data: list = [
        [
            Paragraph("SERVICIO", s["th"]),
            Paragraph("CANT.", s["thr"]),
            Paragraph("P. UNIT.", s["thr"]),
            Paragraph("IMPORTE", s["thr"]),
        ]
    ]
    for it in draft.items:
        svc = Paragraph(_esc(it.servicio or "—"), s["svc"])
        if it.descripcion:
            svc = [svc, Paragraph(_esc(it.descripcion), s["desc"])]
        cant = "—" if it.cantidad is None else f"{it.cantidad:g}"
        data.append(
            [
                svc,
                Paragraph(cant, s["cellr"]),
                Paragraph(_money(it.precio_unitario, None), s["cellr"]),
                Paragraph(_money(it.importe, None), s["cellr"]),
            ]
        )
    if not draft.items:
        data.append([Paragraph("Sin ítems.", s["desc"]), "", "", ""])
    items = Table(
        data,
        colWidths=[usable * 0.52, usable * 0.13, usable * 0.175, usable * 0.175],
        repeatRows=1,
    )
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ]
        )
    )
    totals = Table(
        [
            ["Subtotal", _money(draft.subtotal, cur)],
            ["Impuestos", _money(draft.impuestos, cur)],
            ["TOTAL", _money(draft.total, cur)],
        ],
        colWidths=[usable * 0.18, usable * 0.22],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 1), "Helvetica"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 1), 9.5),
                ("FONTSIZE", (0, 2), (-1, 2), 12),
                ("TEXTCOLOR", (0, 0), (0, 1), MUTED),
                ("TEXTCOLOR", (0, 2), (-1, 2), BRAND),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, 2), (-1, 2), 1, BRAND),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [items, Spacer(1, 10), totals]


def _proposal_footer(canvas, doc) -> None:
    canvas.saveState()
    w, _ = A4
    canvas.setStrokeColor(BORDER)
    canvas.line(2 * cm, 1.45 * cm, w - 2 * cm, 1.45 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.1 * cm, _CONTACT)
    canvas.drawRightString(w - 2 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.restoreState()


def render_proposal_pdf(proposal, title: str) -> bytes:
    """Render de una PROPUESTA COMPLETA (portada + secciones + económica) al estilo CiiSA."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=title or "Propuesta",
    )
    s = _styles()
    s["h2"] = _PS("h2", fontName="Helvetica-Bold", fontSize=13, textColor=BRAND, spaceAfter=2)
    s["body"] = _PS("body", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=14, spaceAfter=5)
    s["bullet"] = _PS(
        "bullet", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=14,
        leftIndent=14, bulletIndent=4, spaceAfter=3,
    )
    s["coverTitle"] = _PS(
        "coverTitle", fontName="Helvetica-Bold", fontSize=26, textColor=BRAND,
        leading=30, alignment=TA_CENTER,
    )
    s["coverSub"] = _PS("coverSub", fontName="Helvetica", fontSize=12, textColor=MUTED, alignment=TA_CENTER)
    usable = A4[0] - 4 * cm
    story: list = []

    # ── Portada ──
    logo_w = 9 * cm
    logo = RLImage(_LOGO_WHITE, width=logo_w, height=logo_w * 97.0 / 674.0)
    band = Table([[logo]], colWidths=[usable])
    band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 26),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 26),
            ]
        )
    )
    story.append(Spacer(1, 40))
    story.append(band)
    story.append(Spacer(1, 70))
    story.append(Paragraph("Propuesta Técnica y<br/>Económica de Servicios", s["coverTitle"]))
    story.append(Spacer(1, 26))
    if proposal.cliente:
        story.append(Paragraph(f"Preparada para: <b>{_esc(proposal.cliente)}</b>", s["coverSub"]))
        story.append(Spacer(1, 6))
    if proposal.fecha:
        story.append(Paragraph(_esc(proposal.fecha), s["coverSub"]))
    story.append(PageBreak())

    # ── Secciones ──
    for sec in proposal.secciones:
        story.append(Paragraph(_esc(sec.titulo), s["h2"]))
        story.append(HRFlowable(width="100%", color=BRAND, thickness=1, spaceAfter=8))
        if sec.key == "economica":
            story.extend(_econ_flowables(proposal.economica, s, usable))
        else:
            story.extend(_content_flowables(sec.contenido, s))
        story.append(Spacer(1, 16))

    doc.build(story, onFirstPage=_proposal_footer, onLaterPages=_proposal_footer)
    return buf.getvalue()
