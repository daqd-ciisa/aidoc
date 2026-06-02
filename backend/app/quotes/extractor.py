"""Extracción de una cotización estructurada desde el contexto de documentos."""
from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.quotes.schema import QuoteDraft
from app.services.llm import get_chat_llm

EXTRACTION_SYSTEM = (
    "Eres un asistente experto en cotizaciones de servicios.\n"
    "A partir del CONTEXTO extraído de los documentos del usuario, completá una "
    "cotización.\n"
    "Devolvé ÚNICAMENTE un objeto JSON válido con EXACTAMENTE estas claves:\n"
    '{"cliente": string|null, "moneda": string|null, '
    '"items": [{"servicio": string, "descripcion": string|null, '
    '"cantidad": number|null, "precio_unitario": number|null, '
    '"importe": number|null}], '
    '"subtotal": number|null, "impuestos": number|null, "total": number|null, '
    '"vigencia": string|null, "condiciones": string|null, "notas": string|null, '
    '"no_encontrado": [string]}\n'
    "Reglas:\n"
    "- Basate SOLO en el contexto. No inventes precios ni datos.\n"
    "- Si un dato no está en el contexto, ponelo en null y agregá su nombre a "
    '"no_encontrado".\n'
    "- No incluyas ningún texto fuera del JSON."
)


GUIDED_SYSTEM = (
    "Eres un asistente experto en cotizaciones de servicios.\n"
    "El usuario necesita una NUEVA cotización. Te paso una cotización PRECEDENTE "
    "existente (parecida) para que la uses como PLANTILLA.\n"
    "Armá la nueva cotización tomando el PRECEDENTE como base:\n"
    "- Reutilizá la estructura, los ítems, precios, moneda y condiciones del "
    "precedente cuando apliquen al nuevo pedido.\n"
    "- Ajustá cantidades, servicios y cliente según el PEDIDO del usuario.\n"
    "- Si el pedido incluye servicios que NO están en el precedente, agregalos con "
    "precio_unitario en null y sumalos a \"no_encontrado\" (no inventes precios).\n"
    "- Recalculá importes/subtotal/total con los precios que sí tengas.\n"
    "- En \"notas\" explicá brevemente en qué te basaste y qué quedó por confirmar.\n"
    "Devolvé ÚNICAMENTE un objeto JSON válido con EXACTAMENTE estas claves:\n"
    '{"cliente": string|null, "moneda": string|null, '
    '"items": [{"servicio": string, "descripcion": string|null, '
    '"cantidad": number|null, "precio_unitario": number|null, '
    '"importe": number|null}], '
    '"subtotal": number|null, "impuestos": number|null, "total": number|null, '
    '"vigencia": string|null, "condiciones": string|null, "notas": string|null, '
    '"no_encontrado": [string]}\n'
    "No incluyas ningún texto fuera del JSON."
)


def _parse_json(raw: str) -> dict:
    """Parseo tolerante: quita fences ```json y recorta al primer objeto {...}."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def extract_quote(context: str, instruction: str) -> QuoteDraft:
    """Llama al LLM (no streaming) y devuelve la cotización validada."""
    # max_tokens amplio: el JSON de una cotización completa supera fácil los
    # 1024 del default y se truncaría a mitad (JSON inválido).
    llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=4096)
    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM),
        HumanMessage(content=f"{instruction}\n\nCONTEXTO:\n{context}"),
    ]
    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(
        response.content
    )
    return QuoteDraft.model_validate(_parse_json(content))


async def draft_from_precedent(precedent: str, request: str) -> QuoteDraft:
    """Genera una NUEVA cotización usando una cotización precedente como plantilla."""
    llm = get_chat_llm(streaming=False, temperature=0.1, max_tokens=4096)
    messages = [
        SystemMessage(content=GUIDED_SYSTEM),
        HumanMessage(
            content=(
                f"PEDIDO DEL USUARIO:\n{request}\n\n"
                f"COTIZACIÓN PRECEDENTE (usá como plantilla):\n{precedent}"
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(
        response.content
    )
    return QuoteDraft.model_validate(_parse_json(content))
