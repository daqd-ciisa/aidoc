"""Endpoints de gestión de documentos: subir, listar, ver, borrar, reindexar."""
from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.connectors.manual_upload import SOURCE_MANUAL
from app.db.models.document import Document, DocumentStatus
from app.db.session import get_db
from app.ingestion.intake import ingest_documents
from app.services import qdrant, storage
from app.services.queue import enqueue_index

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    extension: str
    mime_type: str | None
    size_bytes: int
    status: str
    chunk_count: int
    source: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class UploadResult(BaseModel):
    documents: list[DocumentRead]
    duplicates: list[str]  # nombres omitidos por ser duplicados
    rejected: list[str]  # nombres con extensión no soportada


async def _get_owned(
    db: AsyncSession, tenant_id: str, document_id: str
) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.post("")
async def upload_documents(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> UploadResult:
    items = [
        ((f.filename or "(sin nombre)"), await f.read(), f.content_type)
        for f in files
    ]
    created, duplicates, rejected = await ingest_documents(
        db, tenant_id, items, source=SOURCE_MANUAL
    )

    return UploadResult(
        documents=[DocumentRead.model_validate(d) for d in created],
        duplicates=duplicates,
        rejected=rejected,
    )


@router.get("")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> list[DocumentRead]:
    rows = await db.scalars(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
    )
    return [DocumentRead.model_validate(d) for d in rows]


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> DocumentRead:
    doc = await _get_owned(db, tenant_id, document_id)
    return DocumentRead.model_validate(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    doc = await _get_owned(db, tenant_id, document_id)
    await asyncio.to_thread(qdrant.delete_document_points, doc.id)
    await asyncio.to_thread(storage.delete_object, doc.storage_key)
    await db.delete(doc)
    await db.commit()
    return Response(status_code=204)


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> DocumentRead:
    doc = await _get_owned(db, tenant_id, document_id)
    doc.status = DocumentStatus.PENDING.value
    doc.error = None
    await db.commit()

    task_id = await enqueue_index(doc.id)
    if task_id:
        doc.task_id = task_id
        await db.commit()
    await db.refresh(doc)
    return DocumentRead.model_validate(doc)
