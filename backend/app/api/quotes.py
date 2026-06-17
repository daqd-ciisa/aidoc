"""Endpoints de cotizaciones: generar desde documentos, listar, ver, borrar."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.chat import rag
from app.db.models.approved_url import ApprovedUrl
from app.db.models.document import Document, DocumentStatus, DocumentType
from app.db.models.quote import Quote
from app.db.session import get_db
from app.quotes.catalog import catalog_context
from app.quotes.extractor import (
    draft_from_precedent,
    draft_from_scratch,
    extract_quote,
)
from app.quotes.docx import render_proposal_docx, render_quote_docx
from app.quotes.pdf import render_proposal_pdf, render_quote_pdf
from app.quotes.proposal import ProposalDraft, build_proposal
from app.quotes.schema import QuoteDraft
from app.quotes.summarizer import rerank_precedents
from app.quotes.validation import (
    ValidationReport,
    fetch_live_chunks,
    validate_proposal,
    validate_quote,
)

logger = logging.getLogger("aidoc.quotes")

router = APIRouter(prefix="/quotes", tags=["quotes"])

DEFAULT_INSTRUCTION = (
    "Generá una cotización de servicios a partir de los documentos."
)


class QuoteRequest(BaseModel):
    session_id: str | None = None
    document_ids: list[str] | None = None
    instruction: str | None = None
    title: str | None = None


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    session_id: str | None
    data: dict
    created_at: datetime
    updated_at: datetime


class QuoteGenerated(BaseModel):
    quote_id: str
    title: str
    quote: QuoteDraft
    citations: list[dict]


class QuoteUpdate(BaseModel):
    title: str | None = None
    quote: QuoteDraft


class PrecedentRequest(BaseModel):
    request: str
    top_docs: int | None = None


class Precedent(BaseModel):
    document_id: str
    filename: str
    score: float  # afinidad 0-1 (del rerank LLM, o coseno mecánico de respaldo)
    snippet: str
    motivo: str | None = None  # por qué el LLM lo considera (o no) un buen precedente


class PrecedentsResult(BaseModel):
    precedents: list[Precedent]


class FromPrecedentRequest(BaseModel):
    request: str
    # Uno o varios precedentes. ``document_id`` se mantiene por compatibilidad;
    # ``document_ids`` es el camino nuevo (multi-precedente).
    document_id: str | None = None
    document_ids: list[str] | None = None
    session_id: str | None = None
    title: str | None = None


class FromScratchRequest(BaseModel):
    """Generación SIN precedente (desde cero): solo el pedido en lenguaje natural."""

    request: str
    session_id: str | None = None
    title: str | None = None


class BasedOn(BaseModel):
    document_id: str
    filename: str
    score: float | None = None


class GuidedQuoteResult(BaseModel):
    quote_id: str
    title: str
    quote: QuoteDraft
    based_on: BasedOn | None  # precedente principal (el primero), por compatibilidad
    based_on_all: list[BasedOn] | None = None  # todos los precedentes usados
    citations: list[dict]


_MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]


def _fecha_es(dt: datetime) -> str:
    return f"{dt.day:02d} de {_MESES_ES[dt.month - 1]} de {dt.year}"


def _safe_name(title: str) -> str:
    """Nombre de archivo seguro a partir del título de la cotización."""
    return "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
    ).strip() or "cotizacion"


DEFAULT_VIGENCIA_DIAS = 30


def _default_valida_hasta() -> str:
    """Fecha de validez por defecto (ISO yyyy-mm-dd): hoy + 30 días."""
    return (datetime.now() + timedelta(days=DEFAULT_VIGENCIA_DIAS)).date().isoformat()


class ProposalResult(BaseModel):
    quote_id: str
    title: str
    proposal: ProposalDraft
    based_on: BasedOn | None
    based_on_all: list[BasedOn] | None = None
    citations: list[dict]


class ProposalUpdate(BaseModel):
    title: str | None = None
    proposal: ProposalDraft


_MAX_PRECEDENTS = 4  # tope razonable para no inflar el contexto del LLM


def _precedent_ids(req: FromPrecedentRequest) -> list[str]:
    """Normaliza el/los precedente(s) del request a una lista (dedup, sin vacíos, capada).

    Acepta tanto ``document_ids`` (multi) como ``document_id`` (legacy)."""
    raw = list(req.document_ids or [])
    if req.document_id:
        raw.append(req.document_id)
    seen: set[str] = set()
    out: list[str] = []
    for doc_id in raw:
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            out.append(doc_id)
    return out[:_MAX_PRECEDENTS]


async def _catalog(tenant_id: str, request: str) -> str:
    """Bloque de catálogo relevante al pedido ('' si no hay; nunca lanza)."""
    return await asyncio.to_thread(catalog_context, tenant_id, request)


async def _combine_precedents(
    tenant_id: str, document_ids: list[str]
) -> tuple[str, list[dict], list[BasedOn]]:
    """Recupera uno o varios precedentes completos y los une en un solo contexto.

    Cada documento se etiqueta como ``[PRECEDENTE n: archivo]`` para que el LLM pueda
    distinguirlos. Devuelve ``(contexto_combinado, chunks, based_on)`` — los docs sin
    contenido indexado se omiten silenciosamente."""
    blocks: list[str] = []
    all_chunks: list[dict] = []
    based_on: list[BasedOn] = []
    for doc_id in document_ids:
        context, chunks = await asyncio.to_thread(
            rag.full_document_context, tenant_id, doc_id
        )
        if not context:
            continue
        filename = chunks[0]["filename"] if chunks else "documento"
        blocks.append(f"[PRECEDENTE {len(based_on) + 1}: {filename}]\n{context}")
        all_chunks.extend(chunks)
        based_on.append(BasedOn(document_id=doc_id, filename=filename))
    return "\n\n".join(blocks), all_chunks, based_on


@router.post("/precedents")
async def find_precedents(
    req: PrecedentRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> PrecedentsResult:
    """Paso 1 del flujo guiado: busca cotizaciones parecidas al pedido.

    Recupera candidatos por similitud sobre los resúmenes (alta señal) y luego deja
    que el LLM los reordene por afinidad real y explique el porqué de cada uno."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")
    top = req.top_docs or 3
    # Pool amplio para el reranker: los resúmenes son cortos y el coseno sobre
    # ellos no es del todo confiable para dejar el doc correcto en un pool chico
    # (el LLM sí lo distingue una vez que lo ve). Para bibliotecas chicas esto =
    # rerankear todo.
    try:
        candidates = await asyncio.to_thread(
            rag.rank_documents, req.request, tenant_id, max(top * 5, 25)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo buscando precedentes")
        raise HTTPException(
            status_code=502, detail=f"Búsqueda de precedentes falló: {exc}"
        ) from exc

    if not candidates:
        return PrecedentsResult(precedents=[])

    ranked = await rerank_precedents(req.request, candidates, limit=top)

    precedents: list[Precedent] = []
    for c in ranked[:top]:
        summary = c.get("summary") or {}
        snippet = (
            summary.get("resumen")
            or summary.get("objeto")
            or c.get("summary_text", "")
        )
        precedents.append(
            Precedent(
                document_id=c["document_id"],
                filename=c["filename"],
                score=round(float(c.get("score") or 0.0), 4),
                snippet=(snippet or "")[:300],
                motivo=c.get("motivo"),
            )
        )
    return PrecedentsResult(precedents=precedents)


@router.post("/from-precedent")
async def quote_from_precedent(
    req: FromPrecedentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> GuidedQuoteResult:
    """Paso 2 del flujo guiado: genera la nueva cotización usando el/los precedente(s)
    elegido(s) (documentos completos) como plantilla."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")

    ids = _precedent_ids(req)
    if not ids:
        raise HTTPException(status_code=422, detail="Elegí al menos un precedente.")

    # 1. Recuperar el/los documento(s) precedente(s) completo(s) y combinarlos.
    try:
        context, chunks, based_on = await _combine_precedents(tenant_id, ids)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo recuperando el precedente")
        raise HTTPException(
            status_code=502, detail=f"Recuperación del precedente falló: {exc}"
        ) from exc

    if not context:
        raise HTTPException(
            status_code=404,
            detail="El documento precedente no tiene contenido indexado.",
        )

    # 2. Generar la nueva cotización guiada por el/los precedente(s), anclada al
    # catálogo del tenant (si hay).
    try:
        draft = await draft_from_precedent(
            context, req.request, catalog=await _catalog(tenant_id, req.request)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo generando cotización guiada")
        raise HTTPException(
            status_code=502, detail=f"Generación falló: {exc}"
        ) from exc

    # 3. Persistir.
    draft.valida_hasta = draft.valida_hasta or _default_valida_hasta()
    title = req.title or f"Cotización {draft.cliente or req.request[:40]}".strip()
    quote = Quote(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        session_id=req.session_id,
        title=title,
        data=draft.model_dump(),
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    citations = [
        {
            "ref": i,
            "document_id": c["document_id"],
            "filename": c["filename"],
            "page": c.get("page"),
            "chunk_index": c.get("chunk_index", 0),
            "snippet": c["text"][:300],
            "score": 1.0,
        }
        for i, c in enumerate(chunks[:3], start=1)
    ]

    return GuidedQuoteResult(
        quote_id=quote.id,
        title=quote.title,
        quote=draft,
        based_on=based_on[0] if based_on else None,
        based_on_all=based_on,
        citations=citations,
    )


@router.post("/proposal-from-precedent")
async def proposal_from_precedent(
    req: FromPrecedentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ProposalResult:
    """Genera una PROPUESTA COMPLETA (todas las secciones, no solo la económica)
    usando el/los precedente(s) elegido(s) como plantilla."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")

    ids = _precedent_ids(req)
    if not ids:
        raise HTTPException(status_code=422, detail="Elegí al menos un precedente.")

    # 1. Recuperar el/los documento(s) precedente(s) completo(s) y combinarlos.
    try:
        context, chunks, based_on = await _combine_precedents(tenant_id, ids)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo recuperando el precedente")
        raise HTTPException(
            status_code=502, detail=f"Recuperación del precedente falló: {exc}"
        ) from exc

    if not context:
        raise HTTPException(
            status_code=404,
            detail="El documento precedente no tiene contenido indexado.",
        )

    # 2. Generar la propuesta completa (económica + secciones, en paralelo).
    try:
        proposal = await build_proposal(
            precedent=context,
            request=req.request,
            fecha=_fecha_es(datetime.now()),
            catalog=await _catalog(tenant_id, req.request),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo generando propuesta")
        raise HTTPException(
            status_code=502, detail=f"Generación falló: {exc}"
        ) from exc

    # 3. Persistir (la propuesta completa vive en Quote.data con kind="proposal").
    proposal.economica.valida_hasta = (
        proposal.economica.valida_hasta or _default_valida_hasta()
    )
    title = req.title or f"Cotización {proposal.cliente or req.request[:40]}".strip()
    quote = Quote(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        session_id=req.session_id,
        title=title,
        data=proposal.model_dump(),
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    citations = [
        {
            "ref": i,
            "document_id": c["document_id"],
            "filename": c["filename"],
            "page": c.get("page"),
            "chunk_index": c.get("chunk_index", 0),
            "snippet": c["text"][:300],
            "score": 1.0,
        }
        for i, c in enumerate(chunks[:3], start=1)
    ]

    return ProposalResult(
        quote_id=quote.id,
        title=quote.title,
        proposal=proposal,
        based_on=based_on[0] if based_on else None,
        based_on_all=based_on,
        citations=citations,
    )


@router.post("/from-scratch")
async def quote_from_scratch(
    req: FromScratchRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> GuidedQuoteResult:
    """Genera una cotización económica DESDE CERO (sin precedente ni documentos): un
    esqueleto de ítems desde el pedido, con precios en null para completar a mano."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")

    try:
        draft = await draft_from_scratch(
            req.request, catalog=await _catalog(tenant_id, req.request)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo generando cotización desde cero")
        raise HTTPException(
            status_code=502, detail=f"Generación falló: {exc}"
        ) from exc

    draft.valida_hasta = draft.valida_hasta or _default_valida_hasta()
    title = req.title or f"Cotización {draft.cliente or req.request[:40]}".strip()
    quote = Quote(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        session_id=req.session_id,
        title=title,
        data=draft.model_dump(),
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    return GuidedQuoteResult(
        quote_id=quote.id,
        title=quote.title,
        quote=draft,
        based_on=None,
        based_on_all=[],
        citations=[],
    )


@router.post("/proposal-from-scratch")
async def proposal_from_scratch(
    req: FromScratchRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ProposalResult:
    """Genera una PROPUESTA COMPLETA DESDE CERO (sin precedente): boilerplate fijo de
    CiiSA + secciones redactadas solo desde el pedido + económica esqueleto."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")

    try:
        proposal = await build_proposal(
            precedent=None,
            request=req.request,
            fecha=_fecha_es(datetime.now()),
            catalog=await _catalog(tenant_id, req.request),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo generando propuesta desde cero")
        raise HTTPException(
            status_code=502, detail=f"Generación falló: {exc}"
        ) from exc

    proposal.economica.valida_hasta = (
        proposal.economica.valida_hasta or _default_valida_hasta()
    )
    title = req.title or f"Cotización {proposal.cliente or req.request[:40]}".strip()
    quote = Quote(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        session_id=req.session_id,
        title=title,
        data=proposal.model_dump(),
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    return ProposalResult(
        quote_id=quote.id,
        title=quote.title,
        proposal=proposal,
        based_on=None,
        based_on_all=[],
        citations=[],
    )


@router.post("/generate")
async def generate_quote(
    req: QuoteRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> QuoteGenerated:
    instruction = req.instruction or DEFAULT_INSTRUCTION

    # 1. Recuperar contexto de los documentos (embedding es síncrono → thread).
    try:
        chunks = await asyncio.to_thread(
            rag.retrieve, instruction, tenant_id, req.document_ids
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo en recuperación para cotización")
        raise HTTPException(
            status_code=502, detail=f"Recuperación falló: {exc}"
        ) from exc

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No hay contexto indexado para generar la cotización.",
        )

    # 2. Extraer la cotización estructurada con el LLM (+ catálogo si hay).
    try:
        draft = await extract_quote(
            rag.build_context(chunks),
            instruction,
            catalog=await _catalog(tenant_id, instruction),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo extrayendo cotización")
        raise HTTPException(
            status_code=502, detail=f"Extracción falló: {exc}"
        ) from exc

    # 3. Persistir el borrador.
    draft.valida_hasta = draft.valida_hasta or _default_valida_hasta()
    title = req.title or f"Cotización {draft.cliente or ''}".strip()
    quote = Quote(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        session_id=req.session_id,
        title=title,
        data=draft.model_dump(),
    )
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    return QuoteGenerated(
        quote_id=quote.id,
        title=quote.title,
        quote=draft,
        citations=rag.build_citations(chunks),
    )


@router.get("")
async def list_quotes(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> list[QuoteRead]:
    rows = await db.scalars(
        select(Quote)
        .where(Quote.tenant_id == tenant_id)
        .order_by(Quote.created_at.desc())
    )
    return [QuoteRead.model_validate(q) for q in rows]


@router.get("/{quote_id}")
async def get_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> QuoteRead:
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return QuoteRead.model_validate(quote)


@router.put("/{quote_id}")
async def update_quote(
    quote_id: str,
    req: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> QuoteRead:
    """Guarda los cambios editados manualmente sobre una cotización."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    quote.data = req.quote.model_dump()
    if req.title is not None and req.title.strip():
        quote.title = req.title.strip()
    await db.commit()
    await db.refresh(quote)
    return QuoteRead.model_validate(quote)


@router.put("/{quote_id}/proposal")
async def update_proposal(
    quote_id: str,
    req: ProposalUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> QuoteRead:
    """Guarda los cambios editados manualmente sobre una propuesta completa."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    quote.data = req.proposal.model_dump()
    if req.title is not None and req.title.strip():
        quote.title = req.title.strip()
    await db.commit()
    await db.refresh(quote)
    return QuoteRead.model_validate(quote)


@router.post("/{quote_id}/validate")
async def validate_quote_endpoint(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ValidationReport:
    """Valida las afirmaciones técnicas de la cotización/propuesta contra las
    FUENTES APROBADAS del fabricante (doc_type='reference'), con cita por afirmación."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    # Fuentes aprobadas: URLs (consultadas EN VIVO) + documentos reference indexados.
    url_rows = list(
        await db.scalars(
            select(ApprovedUrl).where(ApprovedUrl.tenant_id == tenant_id)
        )
    )
    has_reference = await db.scalar(
        select(Document.id)
        .where(
            Document.tenant_id == tenant_id,
            Document.doc_type == DocumentType.REFERENCE.value,
            Document.status == DocumentStatus.INDEXED.value,
        )
        .limit(1)
    )
    if not url_rows and not has_reference:
        return ValidationReport(corpus_vacio=True)

    try:
        # Descargar en vivo las URLs aprobadas (degradación segura por URL).
        live_chunks = await fetch_live_chunks(
            [(r.url, r.label) for r in url_rows]
        )
        if isinstance(quote.data, dict) and quote.data.get("kind") == "proposal":
            report = await validate_proposal(
                ProposalDraft.model_validate(quote.data), tenant_id, live_chunks
            )
        else:
            report = await validate_quote(
                QuoteDraft.model_validate(quote.data), tenant_id, live_chunks
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo validando contra fuentes aprobadas")
        raise HTTPException(
            status_code=502, detail=f"Validación falló: {exc}"
        ) from exc

    return report


@router.get("/{quote_id}/pdf")
async def quote_pdf(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Renderiza la cotización/propuesta a un PDF descargable.

    Si el registro es una PROPUESTA completa (``kind="proposal"``) renderiza todas
    las secciones; si es una cotización económica suelta, la tabla económica."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    if isinstance(quote.data, dict) and quote.data.get("kind") == "proposal":
        pdf = render_proposal_pdf(ProposalDraft.model_validate(quote.data), quote.title)
    else:
        draft = QuoteDraft.model_validate(quote.data)
        pdf = render_quote_pdf(draft, quote.title, quote_number=quote.id[:8])

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{_safe_name(quote.title)}.pdf"'},
    )


@router.get("/{quote_id}/docx")
async def quote_docx(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Renderiza la cotización/propuesta a un Word (.docx) editable.

    Espejo del endpoint ``/pdf`` con la misma plantilla CiiSA, para quienes prefieren
    ajustar el documento en Word antes de enviarlo."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    if isinstance(quote.data, dict) and quote.data.get("kind") == "proposal":
        docx = render_proposal_docx(ProposalDraft.model_validate(quote.data), quote.title)
    else:
        draft = QuoteDraft.model_validate(quote.data)
        docx = render_quote_docx(draft, quote.title, quote_number=quote.id[:8])

    return Response(
        content=docx,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_name(quote.title)}.docx"'
        },
    )


@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    await db.delete(quote)
    await db.commit()
    return Response(status_code=204)
