"""Pase de validación de propuestas contra FUENTES APROBADAS del fabricante.

¿Las afirmaciones técnicas de una propuesta (specs, capacidades, modelos) están
respaldadas por documentación aprobada del fabricante? Modo HÍBRIDO:
  - **URLs aprobadas**: se descargan EN VIVO al validar (HPE QuickSpecs, Microsoft
    365 Learn…) y se buscan por coincidencia léxica.
  - **Documentos ``reference``**: corpus ya indexado (para fuentes con login/JS que
    no se pueden leer en vivo, ej. Aruba/Seismic subidos como PDF) → RAG.

Flujo: (1) extraer afirmaciones técnicas verificables (LLM); (2) por cada una,
juntar candidatos de ambas fuentes y emitir un veredicto con cita (LLM):
respaldado / contradice / sin_respaldo.

Degradación segura: una URL caída/bloqueada se omite; un fallo puntual marca esa
afirmación como ``sin_respaldo``. Los precios NO se validan acá (eso es contra el
tarifario interno); este pase es de afirmaciones TÉCNICAS.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass, field

import fitz
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.chat import rag
from app.connectors.web import fetch_url
from app.quotes.extractor import _parse_json
from app.quotes.proposal import ProposalDraft
from app.quotes.schema import QuoteDraft
from app.services.embeddings import get_embeddings
from app.services.llm import get_chat_llm

logger = logging.getLogger("aidoc.quotes.validation")

RESPALDADO = "respaldado"
CONTRADICE = "contradice"
SIN_RESPALDO = "sin_respaldo"
_ESTADOS = {RESPALDADO, CONTRADICE, SIN_RESPALDO}

_MAX_CLAIMS = 12          # tope de afirmaciones a verificar (latencia/costo)
_LIVE_PER_CLAIM = 6       # fragmentos en vivo por afirmación
_CORPUS_PER_CLAIM = 4     # fragmentos del corpus indexado por afirmación
_CHUNK = 1400             # tamaño de fragmento del contenido en vivo
_CHUNK_OVERLAP = 150
_MAX_CHUNKS_PER_URL = 40  # tope de fragmentos por URL (PDFs grandes)


# ── Contenido en vivo de las URLs aprobadas ───────────────────────────────────


# Peso del componente léxico sobre el semántico (igual criterio que rag.retrieve).
_LEX_WEIGHT = 0.4


@dataclass
class LiveChunk:
    text: str
    url: str
    label: str
    vector: list[float] | None = field(default=None, repr=False)


def _split(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    out: list[str] = []
    i = 0
    while i < len(text) and len(out) < _MAX_CHUNKS_PER_URL:
        out.append(text[i : i + _CHUNK])
        i += _CHUNK - _CHUNK_OVERLAP
    return out


def _pdf_text(data: bytes) -> str:
    """Texto plano de un PDF en memoria (sin OCR; las QuickSpecs son texto)."""
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception:  # noqa: BLE001
        return ""


def _fetch_one(url: str, label: str | None) -> list[LiveChunk]:
    """Descarga una URL aprobada y la trocea (vacío si falla; nunca lanza)."""
    try:
        name, data, ctype = fetch_url(url)
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo leer la URL aprobada %s", url, exc_info=True)
        return []
    text = _pdf_text(data) if (ctype or "").startswith("application/pdf") else (
        data.decode("utf-8", errors="replace")
    )
    lbl = (label or "").strip() or name
    return [LiveChunk(text=c, url=url, label=lbl) for c in _split(text)]


async def fetch_live_chunks(sources: list[tuple[str, str | None]]) -> list[LiveChunk]:
    """Descarga EN VIVO todas las URLs aprobadas, las trocea y EMBEBE sus
    fragmentos (para búsqueda semántica, que cruza idiomas y paráfrasis)."""
    if not sources:
        return []
    results = await asyncio.gather(
        *(asyncio.to_thread(_fetch_one, url, label) for url, label in sources)
    )
    chunks: list[LiveChunk] = []
    for r in results:
        chunks.extend(r)
    if not chunks:
        return []
    # Embeber todos los fragmentos en un solo batch. Si falla (sin PCAI), se sigue
    # con ranking solo léxico (vector=None).
    try:
        vectors = await asyncio.to_thread(
            get_embeddings().embed_documents, [c.text for c in chunks]
        )
        for ch, vec in zip(chunks, vectors):
            ch.vector = vec
    except Exception:  # noqa: BLE001
        logger.warning("No se pudieron embeber los fragmentos en vivo", exc_info=True)
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _rank_live(
    claim: str, claim_vec: list[float] | None, chunks: list[LiveChunk], k: int
) -> list[LiveChunk]:
    """Top-k fragmentos en vivo, HÍBRIDO: coseno semántico + boost léxico.

    Mismo criterio que ``rag.retrieve``. El semántico es clave acá porque la
    afirmación puede estar en otro idioma que la fuente (ej. pedido en español,
    QuickSpec/MS Learn en inglés)."""
    if not chunks:
        return []
    terms = rag._query_terms(claim)

    def lex(ch: LiveChunk) -> float:
        if not terms:
            return 0.0
        words = set(re.findall(r"[a-z0-9]+", rag._normalize(ch.text)))
        return sum(1 for t in terms if t in words) / len(terms)

    def score(ch: LiveChunk) -> float:
        sem = _cosine(claim_vec, ch.vector) if (claim_vec and ch.vector) else 0.0
        return sem + _LEX_WEIGHT * lex(ch)

    ranked = sorted(chunks, key=score, reverse=True)
    return ranked[:k]


# ── Modelo de salida ──────────────────────────────────────────────────────────


class ClaimVerdict(BaseModel):
    afirmacion: str
    estado: str  # respaldado | contradice | sin_respaldo
    fuente: str | None = None      # nombre/etiqueta de la fuente que la respalda
    fuente_url: str | None = None  # URL aprobada (si vino de una fuente en vivo)
    snippet: str | None = None
    motivo: str | None = None


class ValidationReport(BaseModel):
    corpus_vacio: bool = False  # no hay URLs aprobadas ni documentos reference
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
    'Si no hay afirmaciones técnicas verificables, devolvé {"afirmaciones": []}.'
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


# ── Verificación de una afirmación (híbrida) ──────────────────────────────────

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


@dataclass
class _Candidate:
    text: str
    label: str
    url: str | None


async def _verify_claim(
    afirmacion: str, tenant_id: str, live_chunks: list[LiveChunk]
) -> ClaimVerdict:
    # Vector de la afirmación para el ranking semántico de las fuentes en vivo.
    claim_vec: list[float] | None = None
    if live_chunks:
        try:
            claim_vec = await asyncio.to_thread(
                get_embeddings().embed_query, afirmacion
            )
        except Exception:  # noqa: BLE001
            claim_vec = None

    candidates: list[_Candidate] = [
        _Candidate(text=ch.text, label=ch.label, url=ch.url)
        for ch in _rank_live(afirmacion, claim_vec, live_chunks, _LIVE_PER_CLAIM)
    ]
    try:
        corpus = await asyncio.to_thread(
            rag.retrieve, afirmacion, tenant_id, None, _CORPUS_PER_CLAIM, "reference"
        )
        candidates.extend(
            _Candidate(text=c.text, label=c.filename, url=None) for c in corpus
        )
    except Exception:  # noqa: BLE001
        logger.warning("Fallo recuperando del corpus reference", exc_info=True)

    if not candidates:
        return ClaimVerdict(
            afirmacion=afirmacion,
            estado=SIN_RESPALDO,
            motivo="No se encontró en las fuentes aprobadas.",
        )

    context = "\n\n---\n\n".join(
        f"[{i}] ({c.label})\n{c.text[:1200]}" for i, c in enumerate(candidates, start=1)
    )
    llm = get_chat_llm(streaming=False, temperature=0.0, max_tokens=400)
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=_VERDICT_SYSTEM),
                HumanMessage(
                    content=f"AFIRMACIÓN:\n{afirmacion}\n\nFRAGMENTOS:\n{context}"
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

    fuente = fuente_url = snippet = None
    if verdict.cita and 1 <= verdict.cita <= len(candidates):
        cited = candidates[verdict.cita - 1]
        fuente = cited.label
        fuente_url = cited.url
        snippet = cited.text[:300]

    return ClaimVerdict(
        afirmacion=afirmacion,
        estado=estado,
        fuente=fuente,
        fuente_url=fuente_url,
        snippet=snippet,
        motivo=(verdict.motivo or "").strip() or None,
    )


# ── Orquestación ───────────────────────────────────────────────────────────────


async def _run(
    text: str, tenant_id: str, live_chunks: list[LiveChunk]
) -> ValidationReport:
    text = (text or "").strip()
    if not text:
        return ValidationReport()
    claims = await _extract_claims(text)
    if not claims:
        return ValidationReport()
    verdicts = await asyncio.gather(
        *(_verify_claim(c, tenant_id, live_chunks) for c in claims)
    )
    report = ValidationReport(afirmaciones=list(verdicts))
    report.respaldadas = sum(1 for v in verdicts if v.estado == RESPALDADO)
    report.contradichas = sum(1 for v in verdicts if v.estado == CONTRADICE)
    report.sin_respaldo = sum(1 for v in verdicts if v.estado == SIN_RESPALDO)
    return report


def _proposal_text(proposal: ProposalDraft) -> str:
    """Contenido TÉCNICO de la propuesta (secciones narrativas + ítems)."""
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


async def validate_proposal(
    proposal: ProposalDraft, tenant_id: str, live_chunks: list[LiveChunk]
) -> ValidationReport:
    return await _run(_proposal_text(proposal), tenant_id, live_chunks)


async def validate_quote(
    draft: QuoteDraft, tenant_id: str, live_chunks: list[LiveChunk]
) -> ValidationReport:
    return await _run(_items_text(draft), tenant_id, live_chunks)
