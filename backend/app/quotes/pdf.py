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
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.quotes.schema import QuoteDraft

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
_LOGO_WHITE = os.path.join(_ASSETS, "ciisa_logo_white.png")  # lockup blanco (fondo navy)
_MARK = os.path.join(_ASSETS, "ciisa_mark.png")  # motivo color: C degradada + acentos (680x470)
_ISOTIPO = os.path.join(_ASSETS, "ciisa_isotipo.png")  # isotipo chico para pie (232x160)
_QR = os.path.join(_ASSETS, "ciisa_qr.png")  # QR de la banda de pie de la portada
_CONTACT = "ciisa.com   ·   México - Colombia   ·   soporte@ciisa.com   ·   (81) 1257-8000"

# Paleta CiiSA real (theme1.xml de las propuestas de muestra): navy #001C71 dominante,
# indigo #332CC4 (banda de portada / header de tabla), lima #BFF500 (banda de categoría),
# cyan #08A7FF (franja divisoria / fechas) y gris #E7E6E6 (bloque de totales).
BRAND = colors.HexColor("#001C71")
INDIGO = colors.HexColor("#332CC4")
LIME = colors.HexColor("#BFF500")
CYAN = colors.HexColor("#08A7FF")
TOTALS_BG = colors.HexColor("#E7E6E6")
BRAND_LIGHT = colors.HexColor("#eaeef4")
INK = colors.HexColor("#1c1917")
MUTED = colors.HexColor("#6b7280")
BORDER = colors.HexColor("#e2e7ef")
ROW_ALT = colors.HexColor("#f6f8fb")

_RAZON_SOCIAL = "CONSULTORIA INTEGRAL DE INFORMATICA S.A.P.I. DE CV"

_PS = ParagraphStyle


def _money(v: float | None, cur: str | None) -> str:
    if v is None:
        return "—"
    s = f"{v:,.2f}"
    # Sin moneda explícita usamos "$" como las propuestas CiiSA (la moneda va aparte).
    return f"{cur} {s}" if cur else f"${s}"


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
        "cellrb": _PS(
            "cellrb",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=INK,
            alignment=TA_RIGHT,
        ),
        "th": _PS("th", fontName="Helvetica-Bold", fontSize=8, textColor=colors.white),
        "thc": _PS(
            "thc",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "thr": _PS(
            "thr",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.white,
            alignment=TA_RIGHT,
        ),
        "cellc": _PS(
            "cellc", fontName="Helvetica", fontSize=9.5, textColor=INK, alignment=TA_CENTER
        ),
        "parte": _PS(
            "parte",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=INDIGO,
            alignment=TA_CENTER,
        ),
        "band": _PS(
            "band",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=BRAND,
            alignment=TA_CENTER,
        ),
        "sect": _PS(
            "sect", fontName="Helvetica-Bold", fontSize=9, textColor=BRAND, spaceAfter=3
        ),
        "body": _PS("body", fontName="Helvetica", fontSize=9, textColor=INK, leading=13),
    }


def _footer(canvas, doc) -> None:
    """Pie como las propuestas CiiSA reales: isotipo abajo a la izquierda y
    "Página N" navy bold cursiva a la derecha (sin línea ni texto extra)."""
    canvas.saveState()
    w, _ = A4
    iso_w = 1.15 * cm
    canvas.drawImage(
        _ISOTIPO, 1.4 * cm, 0.75 * cm,
        width=iso_w, height=iso_w * 160.0 / 232.0, mask="auto",
    )
    canvas.setFont("Helvetica-BoldOblique", 8)
    canvas.setFillColor(BRAND)
    canvas.drawRightString(w - 1.6 * cm, 0.95 * cm, f"Página {doc.page}")
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

    # ── Tabla económica (formato CiiSA, compartida con la propuesta completa) ──
    story.extend(_econ_flowables(draft, s, usable))

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
    """Tabla económica al estilo de las propuestas CiiSA reales: header indigo con
    columnas Ítem/No. Parte/Concepto/Uni./Cant./Precio Unitario/Precio Total, banda
    lima con la categoría de servicio, franja cyan y bloque de totales gris
    (SubTotal/IVA/Total Neto) con Término de Pago/Validez/Moneda a la izquierda.

    Las columnas No. Parte y Uni. solo se muestran si algún ítem trae el dato."""
    has_parte = any(it.no_parte for it in draft.items)
    has_uni = any(it.unidad for it in draft.items)

    # (título, fracción de ancho, estilo header, estilo celda) — Concepto absorbe
    # el ancho de las columnas opcionales ausentes.
    cols = [("Ítem", 0.08, "thc")]
    if has_parte:
        cols.append(("No. Parte", 0.14, "thc"))
    concepto_idx = len(cols)
    cols.append(("Concepto", 0.0, "thc"))
    if has_uni:
        cols.append(("Uni.", 0.08, "thc"))
    cols.append(("Cant.", 0.09, "thc"))
    cols.append(("Precio Unitario", 0.15, "thc"))
    cols.append(("Precio Total", 0.15, "thc"))
    concepto_w = 1.0 - sum(w for _, w, _ in cols)
    widths = [usable * (w or concepto_w) for _, w, _ in cols]
    ncols = len(cols)

    data: list = [[Paragraph(t, s[st]) for t, _, st in cols]]
    styles: list = [
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Padding chico: las columnas angostas (Ítem/Uni./Cant.) no deben quebrar texto.
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
    ]

    # Banda lima con la categoría de servicio, solo sobre la columna Concepto
    # (como en las propuestas reales, donde no cubre todo el ancho de la tabla).
    if draft.categoria:
        row = [""] * ncols
        row[concepto_idx] = Paragraph(_esc(draft.categoria), s["band"])
        data.append(row)
        band_y = len(data) - 1
        styles += [
            ("BACKGROUND", (concepto_idx, band_y), (concepto_idx, band_y), LIME),
            ("TOPPADDING", (0, band_y), (-1, band_y), 4),
            ("BOTTOMPADDING", (0, band_y), (-1, band_y), 4),
        ]

    for n, it in enumerate(draft.items, start=1):
        svc = Paragraph(_esc(it.servicio or "—"), s["svc"])
        if it.descripcion:
            svc = [svc, Paragraph(_esc(it.descripcion), s["desc"])]
        cant = "—" if it.cantidad is None else f"{it.cantidad:g}"
        row = [Paragraph(str(n), s["parte"])]
        if has_parte:
            row.append(Paragraph(_esc(it.no_parte or ""), s["parte"]))
        row.append(svc)
        if has_uni:
            row.append(Paragraph(_esc(it.unidad or ""), s["cellc"]))
        row += [
            Paragraph(cant, s["cellc"]),
            # Precio unitario en bold, como en la tabla CiiSA real.
            Paragraph(_money(it.precio_unitario, None), s["cellrb"]),
            Paragraph(_money(it.importe, None), s["cellr"]),
        ]
        data.append(row)
    if not draft.items:
        data.append([Paragraph("Sin ítems.", s["desc"])] + [""] * (ncols - 1))

    items = Table(data, colWidths=widths, repeatRows=1)
    items.setStyle(TableStyle(styles))

    # Franja divisoria cyan (firma visual de la tabla CiiSA real).
    stripe = Table([[""]], colWidths=[usable], rowHeights=[5])
    stripe.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), CYAN)]))

    # Bloque resumen: acento navy + Término de Pago/Validez/Moneda + totales en gris.
    def _sl(text: str) -> Paragraph:  # etiqueta del bloque izquierdo
        return Paragraph(f"<b>{text}</b>", s["desc"])

    def _sv(text: str | None) -> Paragraph:  # valor del bloque izquierdo
        return Paragraph(_esc(text or "—"), s["desc"])

    accent_w = 0.5 * cm
    left_w, lval_w, tot_l, tot_v = 3.2 * cm, 5.0 * cm, 3.0 * cm, 3.4 * cm
    filler_w = usable - accent_w - left_w - lval_w - tot_l - tot_v
    summary = Table(
        [
            ["", _sl("Término de Pago:"), _sv(draft.termino_pago), "", "SubTotal", _money(draft.subtotal, None)],
            ["", _sl("Validez:"), _sv(draft.vigencia), "", "IVA", _money(draft.impuestos, None)],
            ["", _sl("Moneda:"), _sv(draft.moneda), "", "Total Neto", _money(draft.total, None)],
        ],
        colWidths=[accent_w, left_w, lval_w, filler_w, tot_l, tot_v],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), INDIGO),
                ("BACKGROUND", (4, 0), (-1, -1), TOTALS_BG),
                ("FONTNAME", (4, 0), (-1, 1), "Helvetica"),
                ("FONTNAME", (4, 2), (-1, 2), "Helvetica-Bold"),
                ("FONTSIZE", (4, 0), (-1, -1), 9),
                ("TEXTCOLOR", (4, 0), (-1, -1), INK),
                ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (4, 2), (-1, 2), 1, BRAND),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [items, Spacer(1, 4), stripe, Spacer(1, 8), summary]


# Las páginas interiores de la propuesta usan el mismo pie que la cotización.
_proposal_footer = _footer


def _cover_bg(canvas, doc) -> None:
    """Fondo de la portada estilo CiiSA: página navy completa, banda indigo con el
    nombre del formato, logo blanco arriba a la derecha, motivo geométrico del logo
    (arco "C" + círculo cyan + cuadrado lima) y banda blanca de pie con la razón
    social y el contacto. El título/cliente/fecha van como flowables encima."""
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(BRAND)
    canvas.rect(0, 0, w, h, stroke=0, fill=1)
    # Banda indigo superior izquierda con el nombre del formato.
    canvas.setFillColor(INDIGO)
    canvas.rect(0, h - 4.3 * cm, w * 0.54, 2.5 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(1.3 * cm, h - 2.95 * cm, "Propuesta Técnica y")
    canvas.drawString(1.3 * cm, h - 3.65 * cm, "Económica de Servicios")
    # Logo blanco arriba a la derecha.
    logo_w = 5.4 * cm
    canvas.drawImage(
        _LOGO_WHITE,
        w - logo_w - 1.4 * cm,
        h - 3.6 * cm,
        width=logo_w,
        height=logo_w * 97.0 / 674.0,
        mask="auto",
    )
    # Motivo del isotipo real (C degradada + círculo cyan + cuadrado lima),
    # sangrado al borde izquierdo y ocupando la mayor parte de la página,
    # como en las propuestas de muestra.
    motif_w = 23.5 * cm
    canvas.drawImage(
        _MARK,
        -4.8 * cm,
        h * 0.20,
        width=motif_w,
        height=motif_w * 470.0 / 680.0,  # ≈16.2cm de alto
        mask="auto",
    )
    # Banda blanca de pie con la razón social, el contacto y el QR.
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, w, 2.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(BRAND)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(1.4 * cm, 1.65 * cm, _RAZON_SOCIAL)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.4 * cm, 1.05 * cm, _CONTACT)
    qr_s = 1.8 * cm
    canvas.drawImage(
        _QR, w - qr_s - 1.4 * cm, (2.6 * cm - qr_s) / 2, width=qr_s, height=qr_s,
        mask="auto",
    )
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
        "coverTitle", fontName="Helvetica-Bold", fontSize=21, textColor=colors.white,
        leading=26, alignment=TA_LEFT,
    )
    s["coverDate"] = _PS(
        "coverDate", fontName="Helvetica", fontSize=12, textColor=CYAN,
        alignment=TA_RIGHT,
    )
    usable = A4[0] - 4 * cm
    story: list = []

    # ── Portada (el fondo navy/banda/logo lo pinta _cover_bg en el canvas) ──
    cover_title = _esc(title or "Propuesta")
    if proposal.cliente:
        cover_title = f"{_esc(proposal.cliente)}: {cover_title}"
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph(cover_title, s["coverTitle"]))
    story.append(Spacer(1, 16.5 * cm))
    if proposal.fecha:
        story.append(Paragraph(_esc(proposal.fecha), s["coverDate"]))
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

    doc.build(story, onFirstPage=_cover_bg, onLaterPages=_proposal_footer)
    return buf.getvalue()
