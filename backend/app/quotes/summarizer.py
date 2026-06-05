"""Resumen estructurado de documentos (al indexar) y rerank de precedentes (LLM).

El resumen captura los atributos de alta señal de cada propuesta (tipo, cliente,
objeto, servicios, moneda) para que la búsqueda de precedentes no dependa del
boilerplate (cláusulas de confidencialidad casi idénticas en todas). Se genera al
indexar y se guarda como un punto ``kind="summary"`` en Qdrant.

El rerank usa esos resúmenes + el pedido del usuario para que el LLM ordene los
candidatos por afinidad real (tipo de propuesta y servicios), no solo coseno."""
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.quotes.extractor import _parse_json
from app.services.llm import get_chat_llm

logger = logging.getLogger("aidoc.summarizer")


class DocumentSummary(BaseModel):
    """Resumen de alta señal de una propuesta/cotización."""

    categoria: str | None = None  # "producto" (venta/compra/arrendamiento de bienes) | "servicio"
    tipo: str | None = None  # subcategoría corta: "compra de equipos de cómputo", "bolsa de horas", …
    cliente: str | None = None
    objeto: str | None = None  # 1-2 frases de qué cotiza
    servicios: list[str] = Field(default_factory=list)  # productos/servicios clave
    moneda: str | None = None
    monto_total: float | None = None
    resumen: str | None = None  # 1-2 frases en lenguaje natural


_SUMMARY_SYSTEM = (
    "Eres un asistente que clasifica propuestas y cotizaciones de TI.\n"
    "A partir del TEXTO del documento, devolvé ÚNICAMENTE un objeto JSON con EXACTAMENTE "
    "estas claves:\n"
    '{"categoria": string|null, "tipo": string|null, "cliente": string|null, '
    '"objeto": string|null, "servicios": [string], "moneda": string|null, '
    '"monto_total": number|null, "resumen": string|null}\n'
    "Guía:\n"
    '- "categoria": clasificá la propuesta en UNA de dos:\n'
    '    • "producto" → la propuesta VENDE, COMPRA o ARRIENDA bienes (equipos de '
    "cómputo, laptops, servidores, hardware, licencias). El entregable principal son "
    "los BIENES.\n"
    '    • "servicio" → la propuesta presta TRABAJO/HORAS sobre los equipos del cliente '
    "(instalar, migrar, dar soporte, renovar, auditar, configurar, respaldar). El "
    "entregable principal es la MANO DE OBRA, no los bienes.\n"
    "    Regla clave: si la propuesta entrega/factura los equipos en sí → producto; si "
    "solo trabaja sobre equipos que el cliente ya tiene o comprará aparte → servicio.\n"
    '- "tipo": subcategoría corta y específica. Ejemplos producto: "compra de equipos '
    'de cómputo", "arrendamiento de equipos de cómputo", "compra de hardware/servidores". '
    'Ejemplos servicio: "servicio de despliegue/migración de equipos (personal systems)", '
    '"bolsa de horas de soporte", "servicio de respaldo en la nube", "auditoría de TI", '
    '"infraestructura de red/videovigilancia/control de acceso".\n'
    '- "cliente": empresa a la que va dirigida la propuesta.\n'
    '- "objeto": 1-2 frases describiendo QUÉ se cotiza.\n'
    '- "servicios": palabras clave de los productos/servicios cotizados '
    '(ej: ["laptops Dell", "MacBook", "arrendamiento 36 meses"]).\n'
    '- "moneda": "MXN", "USD" o null.\n'
    '- "monto_total": el total si aparece, si no null.\n'
    "Basate SOLO en el texto. No inventes. No incluyas nada fuera del JSON."
)


def summarize_document(text: str, *, max_chars: int = 9000) -> DocumentSummary | None:
    """Genera el resumen estructurado (SÍNCRONO, para el pipeline de indexado).

    Devuelve ``None`` si el LLM no está disponible o falla (degradación segura);
    el pipeline usa entonces un resumen heurístico de respaldo."""
    if not text.strip():
        return None
    try:
        llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=800)
        messages = [
            SystemMessage(content=_SUMMARY_SYSTEM),
            HumanMessage(content=f"TEXTO DEL DOCUMENTO:\n{text[:max_chars]}"),
        ]
        response = llm.invoke(messages)
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        return DocumentSummary.model_validate(_parse_json(content))
    except Exception as exc:  # noqa: BLE001 — degradación segura
        logger.warning("Resumen LLM falló: %s", exc)
        return None


def summary_to_text(s: DocumentSummary) -> str:
    """Texto compacto y de alta señal del resumen (para embeber y buscar)."""
    lines = []
    if s.categoria:
        lines.append(f"Categoría: {s.categoria}")
    if s.tipo:
        lines.append(f"Tipo de propuesta: {s.tipo}")
    if s.cliente:
        lines.append(f"Cliente: {s.cliente}")
    if s.objeto:
        lines.append(f"Objeto: {s.objeto}")
    if s.servicios:
        lines.append(f"Servicios/productos: {', '.join(s.servicios)}")
    if s.moneda:
        lines.append(f"Moneda: {s.moneda}")
    if s.resumen:
        lines.append(s.resumen)
    return "\n".join(lines)


# ── Rerank de precedentes ───────────────────────────────────────────────────────

_RERANK_SYSTEM = (
    "Eres un asistente que ayuda a elegir, de una biblioteca de cotizaciones previas, "
    "cuáles sirven como PLANTILLA para un nuevo pedido.\n"
    "Te paso el PEDIDO del usuario y una lista de PRECEDENTES (cada uno con su resumen).\n"
    "Ordená TODOS los precedentes de más a menos apropiado para ese pedido y asigná a "
    "cada uno una afinidad 0-100 y un motivo breve.\n"
    "PASO 1 — Detectá la intención del pedido:\n"
    "  • Si el usuario quiere ADQUIRIR/COMPRAR/ARRENDAR bienes (p.ej. 'cotización de "
    "equipos de cómputo', 'laptops', 'servidores', 'hardware') → busca categoría "
    '"producto".\n'
    "  • Si quiere TRABAJO/SERVICIO (soporte, migración, despliegue, auditoría, "
    "respaldo, horas) → busca categoría \"servicio\".\n"
    "PASO 2 — Priorizá FUERTE los precedentes cuya \"Categoría\" coincide con la "
    "intención; un precedente de categoría distinta debe recibir afinidad baja aunque "
    "comparta palabras. Pedir 'equipos de cómputo' = comprar equipos (producto), NO un "
    "servicio de renovación/migración ni de respaldo.\n"
    "PASO 3 — Dentro de la categoría correcta, desempatá por coincidencia de TIPO y de "
    "SERVICIOS/PRODUCTOS.\n"
    "Considerá TODOS los precedentes, pero devolvé SOLO los más apropiados (la cantidad "
    "que pida el usuario), ordenados de mejor a peor. El \"motivo\" debe ser BREVE "
    "(una frase, máx 20 palabras).\n"
    "Devolvé ÚNICAMENTE un objeto JSON:\n"
    '{"precedentes": [{"id": number, "afinidad": number, "motivo": string}]}\n'
    "donde \"id\" es el número del precedente. Nada fuera del JSON."
)


async def rerank_precedents(
    request: str, candidates: list[dict], *, limit: int = 5
) -> list[dict]:
    """Reordena ``candidates`` por afinidad con ``request`` usando el LLM.

    ``candidates``: lista de dicts con al menos ``document_id``, ``filename`` y
    ``summary_text``. El LLM evalúa todos pero solo devuelve los ``limit`` mejores con
    ``motivo`` (acota los tokens generados = latencia). El resto se anexa al final en
    el orden mecánico (sin motivo). Degrada al orden original si el LLM falla."""
    if not candidates:
        return []

    listing = "\n\n".join(
        f"[{i}] {c.get('filename', 'documento')}\n{c.get('summary_text', '').strip()}"
        for i, c in enumerate(candidates)
    )
    try:
        llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=600)
        messages = [
            SystemMessage(content=_RERANK_SYSTEM),
            HumanMessage(
                content=(
                    f"PEDIDO:\n{request}\n\n"
                    f"Devolvé los {limit} precedentes más apropiados.\n\n"
                    f"PRECEDENTES:\n{listing}"
                )
            ),
        ]
        response = await llm.ainvoke(messages)
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        data = _parse_json(content)
        ranking = data.get("precedentes", []) if isinstance(data, dict) else []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rerank LLM falló, uso orden mecánico: %s", exc)
        ranking = []

    out: list[dict] = []
    seen: set[int] = set()
    for item in ranking:
        try:
            idx = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(candidates) or idx in seen:
            continue
        seen.add(idx)
        c = dict(candidates[idx])
        afinidad = item.get("afinidad")
        try:
            c["score"] = max(0.0, min(1.0, float(afinidad) / 100.0))
        except (TypeError, ValueError):
            pass  # conserva el score mecánico
        motivo = item.get("motivo")
        if isinstance(motivo, str):
            c["motivo"] = motivo.strip()
        out.append(c)

    # Cualquier candidato que el LLM no devolvió, va al final en su orden mecánico.
    for i, c in enumerate(candidates):
        if i not in seen:
            out.append(dict(c))
    return out
