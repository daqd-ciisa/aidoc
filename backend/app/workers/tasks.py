"""Tareas del worker ARQ."""
from __future__ import annotations

import asyncio
import logging

from app.db.models.document import Document, DocumentStatus
from app.db.session import AsyncSessionLocal
from app.ingestion.pipeline import run_indexing

logger = logging.getLogger("aidoc.worker")


async def index_document(ctx: dict, document_id: str) -> None:
    """Indexa un documento: pending → processing → indexed/failed."""
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            logger.warning("index_document: documento %s no existe", document_id)
            return
        doc.status = DocumentStatus.PROCESSING.value
        doc.error = None
        await db.commit()
        tenant_id, storage_key, filename, extension = (
            doc.tenant_id,
            doc.storage_key,
            doc.filename,
            doc.extension,
        )

    try:
        chunk_count = await asyncio.to_thread(
            run_indexing,
            document_id=document_id,
            tenant_id=tenant_id,
            storage_key=storage_key,
            filename=filename,
            extension=extension,
        )
    except Exception as exc:  # noqa: BLE001 — registrar el fallo en el documento
        logger.exception("Fallo indexando %s", document_id)
        async with AsyncSessionLocal() as db:
            doc = await db.get(Document, document_id)
            if doc is not None:
                doc.status = DocumentStatus.FAILED.value
                doc.error = str(exc)[:2000]
                await db.commit()
        return

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is not None:
            doc.status = DocumentStatus.INDEXED.value
            doc.chunk_count = chunk_count
            doc.error = None
            await db.commit()
    logger.info("Documento %s indexado (%d chunks)", document_id, chunk_count)
