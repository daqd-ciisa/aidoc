"""Pipeline de indexado (SÍNCRONO): descarga → parse → chunk → embed → upsert.

Se ejecuta dentro de un thread desde el worker async para no bloquear el loop.
Es reindex-safe: borra los vectores previos del documento antes de subir.
"""
from __future__ import annotations

import logging
import os
import tempfile

from app.ingestion.chunker import chunk_pages
from app.ingestion.parsers import get_parser
from app.quotes.summarizer import DocumentSummary, summarize_document, summary_to_text
from app.services import qdrant, storage
from app.services.embeddings import get_embeddings

logger = logging.getLogger("aidoc.pipeline")


def run_indexing(
    *,
    document_id: str,
    tenant_id: str,
    storage_key: str,
    filename: str,
    extension: str,
    doc_type: str = "document",
) -> int:
    """Indexa un documento ya almacenado. Devuelve el nº de chunks subidos."""
    parser = get_parser(extension)
    if parser is None:
        raise ValueError(f"Formato no soportado: {extension}")

    data = storage.download_bytes(storage_key)

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        pages = parser(tmp_path)
    finally:
        os.unlink(tmp_path)

    chunks = chunk_pages(pages)

    # Limpiar vectores previos (reindex) antes de subir los nuevos.
    qdrant.delete_document_points(document_id)

    if not chunks:
        return 0

    embeddings = get_embeddings()
    vectors = embeddings.embed_documents([c.text for c in chunks])
    qdrant.upsert_chunks(
        tenant_id=tenant_id,
        document_id=document_id,
        filename=filename,
        chunks=chunks,
        vectors=vectors,
        doc_type=doc_type,
    )

    # Resumen de alta señal para la búsqueda de precedentes (punto kind="summary").
    # Los catálogos y las fuentes aprobadas NO son precedentes: sin punto summary
    # nunca compiten como plantilla de cotización (su rol es ser referencia).
    if doc_type not in ("catalog", "reference"):
        _index_summary(
            embeddings=embeddings,
            document_id=document_id,
            tenant_id=tenant_id,
            filename=filename,
            full_text="\n".join(c.text for c in chunks),
        )
    return len(chunks)


def _index_summary(*, embeddings, document_id, tenant_id, filename, full_text) -> None:
    """Genera el resumen del documento y sube su punto vectorial. Degradación
    segura: si el LLM no está, usa un resumen heurístico para que el documento
    igual sea hallable como precedente."""
    summary = summarize_document(full_text)
    if summary is not None and summary_to_text(summary).strip():
        summary_text = summary_to_text(summary)
    else:  # fallback: el documento debe seguir siendo hallable como precedente
        summary = summary or DocumentSummary()
        summary.resumen = full_text[:600]
        summary_text = f"{filename}\n{full_text[:600]}"
    try:
        vector = embeddings.embed_documents([summary_text])[0]
        qdrant.upsert_summary(
            tenant_id=tenant_id,
            document_id=document_id,
            filename=filename,
            vector=vector,
            summary_text=summary_text,
            summary=summary.model_dump(),
        )
    except Exception as exc:  # noqa: BLE001 — no romper el indexado por el resumen
        logger.warning("No se pudo indexar el resumen de %s: %s", document_id, exc)
