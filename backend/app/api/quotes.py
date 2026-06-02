"""Endpoints de cotizaciones: generar desde documentos, listar, ver, borrar."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.chat import rag
from app.db.models.quote import Quote
from app.db.session import get_db
from app.quotes.extractor import draft_from_precedent, extract_quote
from app.quotes.pdf import render_quote_pdf
from app.quotes.schema import QuoteDraft

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


class PrecedentRequest(BaseModel):
    request: str
    top_docs: int | None = None


class Precedent(BaseModel):
    document_id: str
    filename: str
    score: float
    hits: int
    snippet: str


class PrecedentsResult(BaseModel):
    precedents: list[Precedent]


class FromPrecedentRequest(BaseModel):
    request: str
    document_id: str
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
    based_on: BasedOn | None
    citations: list[dict]


@router.post("/precedents")
async def find_precedents(
    req: PrecedentRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> PrecedentsResult:
    """Paso 1 del flujo guiado: busca cotizaciones existentes parecidas al pedido."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")
    try:
        ranked = await asyncio.to_thread(
            rag.rank_documents, req.request, tenant_id, 40, req.top_docs or 3
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo buscando precedentes")
        raise HTTPException(
            status_code=502, detail=f"Búsqueda de precedentes falló: {exc}"
        ) from exc

    return PrecedentsResult(
        precedents=[
            Precedent(
                document_id=g["document_id"],
                filename=g["filename"],
                score=round(g["best_score"], 4),
                hits=g["hits"],
                snippet=g["snippet"],
            )
            for g in ranked
        ]
    )


@router.post("/from-precedent")
async def quote_from_precedent(
    req: FromPrecedentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> GuidedQuoteResult:
    """Paso 2 del flujo guiado: genera la nueva cotización usando el precedente
    elegido (documento completo) como plantilla."""
    if not req.request.strip():
        raise HTTPException(status_code=422, detail="El pedido no puede estar vacío.")

    # 1. Recuperar el documento precedente completo.
    try:
        context, chunks = await asyncio.to_thread(
            rag.full_document_context, tenant_id, req.document_id
        )
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

    filename = chunks[0]["filename"] if chunks else "documento"

    # 2. Generar la nueva cotización guiada por el precedente.
    try:
        draft = await draft_from_precedent(context, req.request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo generando cotización guiada")
        raise HTTPException(
            status_code=502, detail=f"Generación falló: {exc}"
        ) from exc

    # 3. Persistir.
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
        based_on=BasedOn(document_id=req.document_id, filename=filename),
        citations=citations,
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

    # 2. Extraer la cotización estructurada con el LLM.
    try:
        draft = await extract_quote(rag.build_context(chunks), instruction)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo extrayendo cotización")
        raise HTTPException(
            status_code=502, detail=f"Extracción falló: {exc}"
        ) from exc

    # 3. Persistir el borrador.
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


@router.get("/{quote_id}/pdf")
async def quote_pdf(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    """Renderiza la cotización a un PDF descargable."""
    quote = await db.get(Quote, quote_id)
    if quote is None or quote.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    draft = QuoteDraft.model_validate(quote.data)
    pdf = render_quote_pdf(draft, quote.title, quote_number=quote.id[:8])

    safe = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in quote.title
    ).strip() or "cotizacion"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe}.pdf"'},
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
