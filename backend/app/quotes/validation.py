"""Pase de validación de propuestas contra las FUENTES APROBADAS del fabricante.

¿Las afirmaciones técnicas de una propuesta (specs, capacidades, modelos) están
respaldadas por la documentación aprobada (``doc_type="reference"``: HPE
QuickSpecs, guías validadas de Aruba, Microsoft 365 Learn…)?

Flujo:
  1. Extraer del contenido de la propuesta las afirmaciones técnicas VERIFICABLES (LLM).
  2. Por cada afirmación, recuperar de las fuentes aprobadas (RAG filtrado a
     ``reference``) y emitir un veredicto con cita: respaldado / contradice /
     sin_respaldo (LLM).

Degradación segura: sin corpus aprobado el endpoint devuelve ``corpus_vacio``;
un fallo puntual marca esa afirmación como ``sin_respaldo`` sin romper el resto.
NOTA: los precios NO se validan acá (eso es contra el tarifario interno); este
pase es de afirmaciones TÉCNICAS.
"""
from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.chat import rag
from app.quotes.extractor import _parse_json
from app.quotes.proposal import ProposalDraft
from app.quotes.schema import QuoteDraft
from app.services.llm import get_chat_llm

logger = logging.getLogger("aidoc.quotes.validation")

# Estados posibles de un veredicto.
RESPALDADO = "respaldado"
CONTRADICE = "contradice"
SIN_RESPALDO = "sin_respaldo"
_ESTADOS = {RESPALDADO, CONTRADICE, SIN_RESPALDO}

_MAX_CLAIMS = 12  # tope de afirmaciones a verificar (latencia/costo)
_VERIFY_TOP_K = 5  # fragmentos de fuentes aprobadas por afirmación


# ── Modelo de salida ──────────────────────────────────────────────────────────


class ClaimVerdict(BaseModel):
    afirmacion: str
    estado: str  # respaldado | contradice | sin_respaldo
    fuente: str | None = None  # nombre del documento aprobado que la respalda
    snippet: str | None = None  # fragmento citado de esa fuente
    motivo: str | None = None  # explicación breve del veredicto


class ValidationReport(BaseModel):
    corpus_vacio: bool = False  # no hay fuentes aprobadas indexadas
    afirmaciones: list[ClaimVerdict] = Field(default_factory=list)
    respaldadas: int = 0
    contradichas: int = 0
    sin_respaldo: int = 0


# ── Extracción de afirmaciones ─────────────────────────────────────────────────

_CLAIMS_SYSTEM = (
    "Eres un revisor técnico. Te paso el contenido de una propuesta de TI.\n"
    "Extraé las AFIRMACIONES TÉCNICAS VERIFICABLES: especificaciones de producto, "
    "capacidades, modelos, versiones, compatibilidades o cantidades técnicas que "
    "podrían contrastarse contra la documentación del fabricante.\n"
    "IGNORÁ: texto comercial, objetivos genéricos, condiciones de pago, precios, "
    "plazos, cláusulas legales y todo lo que no sea una característica técnica "
    "concreta.\n"
    "Cada afirmación debe ser ATÓMICA (una sola cosa) y AUTOCONTENIDA (entendible "
    "sin contexto: incluí el producto/modelo al que se refiere).\n"
    f"Devolvé como máximo {_MAX_CLAIMS}, ÚNICAMENTE este JSON: "
    '{"afirmaciones": ["...", "..."]}\n'
    "Si no hay afirmaciones técnicas verificables, devolvé "
    '{"afirmaciones": []}.'
)


class _Claims(BaseModel):
    afirmaciones: list[str] = Field(default_factory=list)


async def _extract_claims(text: str) -> list[str]:
    llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=1024)
    response = await llm.ainvoke(
        [SystemMessage(content=_CLAIMS_SYSTEM), HumanMessage(content=text)]
    )
    content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    data = _Claims.model_validate(_parse_json(content))
    out: list[str] = []
    seen: set[str] = set()
    for a in data.afirmaciones:
        a = (a or "").strip()
        if a and a.lower() not in seen:
            seen.add(a.lower())
            out.append(a)
    return out[:_MAX_CLAIMS]


# ── Verificación de una afirmación ─────────────────────────────────────────────

_VERDICT_SYSTEM = (
    "Eres un verificador técnico riguroso. Te paso UNA AFIRMACIÓN técnica y "
    "FRAGMENTOS de documentación APROBADA del fabricante, cada uno con un marcador "
    "[n].\n"
    "Determiná si los fragmentos respaldan la afirmación:\n"
    '- "respaldado": un fragmento confirma claramente la afirmación.\n'
    '- "contradice": un fragmento dice algo incompatible con la afirmación.\n'
    '- "sin_respaldo": los fragmentos no permiten confirmar ni desmentir.\n'
    "Sé estricto: si no está claramente confirmado, es sin_respaldo. NO uses "
    "conocimiento externo, SOLO los fragmentos.\n"
    'Devolvé ÚNICAMENTE este JSON: {"estado": "respaldado|contradice|sin_respaldo", '
    '"cita": <número del fragmento [n] decisivo o null>, "motivo": "<una frase breve>"}'
)


class _Verdict(BaseModel):
    estado: str | None = None
    cita: int | None = None
    motivo: str | None = None


async def _verify_claim(afirmacion: str, tenant_id: str) -> ClaimVerdict:
    try:
        chunks = await asyncio.to_thread(
            rag.retrieve, afirmacion, tenant_id, None, _VERIFY_TOP_K, "reference"
        )
    except Exception:  # noqa: BLE001 — sin recuperación, queda sin respaldo
        logger.warning("Fallo recuperando fuentes para una afirmación", exc_info=True)
        chunks = []

    if not chunks:
        return ClaimVerdict(
            afirmacion=afirmacion,
            estado=SIN_RESPALDO,
            motivo="No se encontró en las fuentes aprobadas.",
        )

    llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=400)
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_VERDICT_SYSTEM),
                HumanMessage(
                    content=(
                        f"AFIRMACIÓN:\n{afirmacion}\n\n"
                        f"FRAGMENTOS DE FUENTES APROBADAS:\n{rag.build_context(chunks)}"
                    )
                ),
            ]
        )
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        verdict = _Verdict.model_validate(_parse_json(content))
    except Exception:  # noqa: BLE001
        logger.warning("Fallo verificando una afirmación", exc_info=True)
        return ClaimVerdict(
            afirmacion=afirmacion, estado=SIN_RESPALDO, motivo="No se pudo verificar."
        )

    estado = (verdict.estado or "").strip().lower()
    if estado not in _ESTADOS:
        estado = SIN_RESPALDO

    fuente = snippet = None
    if verdict.cita and 1 <= verdict.cita <= len(chunks):
        cited = chunks[verdict.cita - 1]
        fuente = cited.filename
        snippet = cited.text[:300]

    return ClaimVerdict(
        afirmacion=afirmacion,
        estado=estado,
        fuente=fuente,
        snippet=snippet,
        motivo=(verdict.motivo or "").strip() or None,
    )


# ── Orquestación ───────────────────────────────────────────────────────────────


async def _run(text: str, tenant_id: str) -> ValidationReport:
    text = (text or "").strip()
    if not text:
        return ValidationReport()
    claims = await _extract_claims(text)
    if not claims:
        return ValidationReport()
    verdicts = await asyncio.gather(*(_verify_claim(c, tenant_id) for c in claims))
    report = ValidationReport(afirmaciones=list(verdicts))
    report.respaldadas = sum(1 for v in verdicts if v.estado == RESPALDADO)
    report.contradichas = sum(1 for v in verdicts if v.estado == CONTRADICE)
    report.sin_respaldo = sum(1 for v in verdicts if v.estado == SIN_RESPALDO)
    return report


def _proposal_text(proposal: ProposalDraft) -> str:
    """Junta el contenido TÉCNICO de la propuesta (secciones narrativas + ítems).

    Excluye boilerplate fijo (Acerca de/Confidencialidad/Condiciones comerciales)."""
    parts: list[str] = []
    for sec in proposal.secciones:
        if sec.key in ("objetivo", "alcances", "limitantes", "terminos"):
            if sec.contenido.strip():
                parts.append(f"{sec.titulo}:\n{sec.contenido}")
    parts.append(_items_text(proposal.economica))
    return "\n\n".join(p for p in parts if p.strip())


def _items_text(draft: QuoteDraft) -> str:
    lines: list[str] = []
    for it in draft.items:
        line = it.servicio or ""
        if it.descripcion:
            line += f" — {it.descripcion}"
        if it.no_parte:
            line += f" (No. parte {it.no_parte})"
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)


async def validate_proposal(proposal: ProposalDraft, tenant_id: str) -> ValidationReport:
    return await _run(_proposal_text(proposal), tenant_id)


async def validate_quote(draft: QuoteDraft, tenant_id: str) -> ValidationReport:
    return await _run(_items_text(draft), tenant_id)
