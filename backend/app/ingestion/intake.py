"""Ingesta compartida: almacenar bytes → crear Document → encolar indexado.

Lo usan tanto la subida manual como los conectores (Google Drive, etc.), para
que todos sigan exactamente el mismo camino (dedup por hash, storage, ARQ)."""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentStatus, DocumentType
from app.ingestion.parsers import SUPPORTED_EXTENSIONS
from app.services import storage
from app.services.queue import enqueue_index

# Un item de ingesta: (nombre, bytes, content_type).
IntakeItem = tuple[str, bytes, str | None]


async def ingest_documents(
    db: AsyncSession,
    tenant_id: str,
    items: list[IntakeItem],
    source: str,
    doc_type: str = DocumentType.DOCUMENT.value,
    origin_url: str | None = None,
) -> tuple[list[Document], list[str], list[str]]:
    """Procesa una lista de archivos. Devuelve (creados, duplicados, rechazados).

    - rechazado: extensión no soportada.
    - duplicado: ya existe un documento con el mismo sha256 en el tenant.
    - ``doc_type``: ``"document"`` (default), ``"catalog"`` (material de
      referencia para cotizaciones) o ``"reference"`` (fuente aprobada externa).
    - ``origin_url``: URL de origen de una fuente aprobada por web (ver Document).
    """
    created: list[Document] = []
    duplicates: list[str] = []
    rejected: list[str] = []

    for name, data, content_type in items:
        ext = Path(name).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            rejected.append(name)
            continue

        content_hash = hashlib.sha256(data).hexdigest()
        existing = await db.scalar(
            select(Document).where(
                Document.tenant_id == tenant_id,
                Document.content_hash == content_hash,
            )
        )
        if existing is not None:
            duplicates.append(name)
            continue

        doc_id = str(uuid.uuid4())
        storage_key = f"{tenant_id}/{doc_id}{ext}"
        await asyncio.to_thread(
            storage.upload_bytes, storage_key, data, content_type
        )

        doc = Document(
            id=doc_id,
            tenant_id=tenant_id,
            filename=name,
            extension=ext,
            mime_type=content_type,
            size_bytes=len(data),
            content_hash=content_hash,
            storage_key=storage_key,
            source=source,
            doc_type=doc_type,
            origin_url=origin_url,
            status=DocumentStatus.PENDING.value,
        )
        db.add(doc)
        created.append(doc)

    await db.commit()

    for doc in created:
        await db.refresh(doc)
        task_id = await enqueue_index(doc.id)
        if task_id:
            doc.task_id = task_id
    await db.commit()
    for doc in created:
        await db.refresh(doc)

    return created, duplicates, rejected
