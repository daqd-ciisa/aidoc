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
    '"categoria": string|null, "termino_pago": string|null, '
    '"items": [{"servicio": string, "descripcion": string|null, '
    '"no_parte": string|null, "unidad": string|null, '
    '"cantidad": number|null, "precio_unitario": number|null, '
    '"importe": number|null}], '
    '"subtotal": number|null, "impuestos": number|null, "total": number|null, '
    '"vigencia": string|null, "condiciones": string|null, "notas": string|null, '
    '"no_encontrado": [string]}\n'
    "Reglas:\n"
    "- Basate SOLO en el contexto. No inventes precios ni datos.\n"
    '- "categoria" es la línea de servicio (ej. "Servicios Personal Systems"); '
    '"no_parte" el código de parte (ej. "SRV26014"); "unidad" la unidad de medida '
    '(ej. "Serv", "Pza"); "termino_pago" la forma de pago (ej. "50% al inicio / 50% '
    'al finalizar"). Si no están en el contexto, dejalos en null.\n'
    "- Si un dato no está en el contexto, ponelo en null y agregá su nombre a "
    '"no_encontrado".\n'
    "- No incluyas ningún texto fuera del JSON."
)


GUIDED_SYSTEM = (
    "Eres un asistente experto en cotizaciones de servicios.\n"
    "El usuario necesita una NUEVA cotización. Te paso UNA O VARIAS cotizaciones "
    "PRECEDENTES existentes (parecidas), cada una etiquetada como "
    "[PRECEDENTE n: archivo], para que las uses como PLANTILLA.\n"
    "Armá la nueva cotización tomando los PRECEDENTES como base:\n"
    "- Si hay VARIOS, usá el más cercano al pedido como estructura/plantilla principal "
    "y completá ítems, precios o datos que falten tomándolos de los otros.\n"
    "- Reutilizá la estructura, los ítems, precios, moneda y condiciones de los "
    "precedentes cuando apliquen al nuevo pedido.\n"
    "- Reutilizá también no_parte, unidad, categoria y termino_pago de los precedentes "
    "cuando el ítem/servicio sea el mismo; NO inventes códigos de parte nuevos.\n"
    "- Ajustá cantidades, servicios y cliente según el PEDIDO del usuario.\n"
    "- Si hay CONFLICTO entre precedentes (p. ej. distinta moneda o precios distintos "
    "para lo mismo), priorizá el PRIMER precedente y aclaralo en \"notas\".\n"
    "- Si el pedido incluye servicios que NO están en ningún precedente, agregalos con "
    "precio_unitario en null y sumalos a \"no_encontrado\" (no inventes precios).\n"
    "- Recalculá importes/subtotal/total con los precios que sí tengas.\n"
    "- En \"notas\" explicá brevemente en qué precedente(s) te basaste y qué quedó por "
    "confirmar. NO uses las etiquetas internas [PRECEDENTE n] en el texto: referite a "
    "los documentos por su contenido o nombre.\n"
    "Devolvé ÚNICAMENTE un objeto JSON válido con EXACTAMENTE estas claves:\n"
    '{"cliente": string|null, "moneda": string|null, '
    '"categoria": string|null, "termino_pago": string|null, '
    '"items": [{"servicio": string, "descripcion": string|null, '
    '"no_parte": string|null, "unidad": string|null, '
    '"cantidad": number|null, "precio_unitario": number|null, '
    '"importe": number|null}], '
    '"subtotal": number|null, "impuestos": number|null, "total": number|null, '
    '"vigencia": string|null, "condiciones": string|null, "notas": string|null, '
    '"no_encontrado": [string]}\n'
    "No incluyas ningún texto fuera del JSON."
)


SCRATCH_SYSTEM = (
    "Eres un asistente experto en cotizaciones de servicios.\n"
    "El usuario necesita una NUEVA cotización pero NO hay precedente ni documentos de "
    "referencia. Armá un ESQUELETO de cotización a partir del PEDIDO:\n"
    "- Incluí UN ítem por cada entregable o servicio principal mencionado o implícito "
    "en el pedido (NO resumas todo en un solo ítem genérico).\n"
    "- Poné la cantidad que el usuario haya indicado; si no la dio, dejala en null.\n"
    "- NO inventes precios: precio_unitario e importe SIEMPRE en null, y agregá cada "
    'ítem sin precio a "no_encontrado".\n'
    "- Dejá subtotal/impuestos/total en null (se completan al cargar los precios).\n"
    "- Dejá no_parte, categoria y termino_pago en null (se completan después); "
    '"unidad" podés inferirla del tipo de ítem (ej. "Serv" o "Pza").\n'
    '- En "notas" aclará que es un borrador desde cero, para completar manualmente.\n'
    "Devolvé ÚNICAMENTE un objeto JSON válido con EXACTAMENTE estas claves:\n"
    '{"cliente": string|null, "moneda": string|null, '
    '"categoria": string|null, "termino_pago": string|null, '
    '"items": [{"servicio": string, "descripcion": string|null, '
    '"no_parte": string|null, "unidad": string|null, '
    '"cantidad": number|null, "precio_unitario": number|null, '
    '"importe": number|null}], '
    '"subtotal": number|null, "impuestos": number|null, "total": number|null, '
    '"vigencia": string|null, "condiciones": string|null, "notas": string|null, '
    '"no_encontrado": [string]}\n'
    "No incluyas ningún texto fuera del JSON."
)


_LABEL_NAMED = re.compile(r"\[PRECEDENTE\s*\d+\s*:\s*([^\]]+)\]")
_LABEL_PLAIN = re.compile(r"\[PRECEDENTE\s*\d+\s*\]")


def strip_precedent_labels(text: str | None) -> str | None:
    """Quita las etiquetas internas ``[PRECEDENTE n: archivo]`` del texto de salida.

    El LLM a veces filtra estas etiquetas (que usamos para separar precedentes en el
    contexto) en notas/condiciones; las reemplazamos por algo legible para el usuario."""
    if not text:
        return text
    text = _LABEL_NAMED.sub(lambda m: f"«{m.group(1).strip()}»", text)
    return _LABEL_PLAIN.sub("el precedente principal", text)


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


async def draft_from_scratch(request: str) -> QuoteDraft:
    """Genera un esqueleto de cotización SOLO desde el pedido (sin precedente ni docs).

    Pensado para el caso "no hay precedente": el LLM propone los ítems probables y deja
    los precios en null/no_encontrado para que el usuario los cargue a mano.

    Temperatura 0.0 para que el esqueleto sea estable y completo (mismo pedido → mismos
    ítems), tanto solo como dentro de la propuesta completa."""
    llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=4096)
    messages = [
        SystemMessage(content=SCRATCH_SYSTEM),
        HumanMessage(content=f"PEDIDO DEL USUARIO:\n{request}"),
    ]
    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(
        response.content
    )
    return QuoteDraft.model_validate(_parse_json(content))


async def draft_from_precedent(precedent: str, request: str) -> QuoteDraft:
    """Genera una NUEVA cotización usando uno o varios precedentes como plantilla.

    ``precedent`` puede contener uno o varios documentos completos, cada uno etiquetado
    como ``[PRECEDENTE n: archivo]`` (ver ``api.quotes._combine_precedents``)."""
    llm = get_chat_llm(streaming=False, temperature=0.1, max_tokens=4096)
    messages = [
        SystemMessage(content=GUIDED_SYSTEM),
        HumanMessage(
            content=(
                f"PEDIDO DEL USUARIO:\n{request}\n\n"
                f"PRECEDENTE(S) (usá como plantilla):\n{precedent}"
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else str(
        response.content
    )
    draft = QuoteDraft.model_validate(_parse_json(content))
    draft.notas = strip_precedent_labels(draft.notas)
    draft.condiciones = strip_precedent_labels(draft.condiciones)
    return draft
