"""Pipeline de indexado (SÍNCRONO): descarga → parse → chunk → embed → upsert.

Se ejecuta dentro de un thread desde el worker async para no bloquear el loop.
Es reindex-safe: borra los vectores previos del documento antes de subir.
"""
from __future__ import annotations

import os
import tempfile

from app.ingestion.chunker import chunk_pages
from app.ingestion.parsers import get_parser
from app.services import qdrant, storage
from app.services.embeddings import get_embeddings


def run_indexing(
    *,
    document_id: str,
    tenant_id: str,
    storage_key: str,
    filename: str,
    extension: str,
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

    vectors = get_embeddings().embed_documents([c.text for c in chunks])
    qdrant.upsert_chunks(
        tenant_id=tenant_id,
        document_id=document_id,
        filename=filename,
        chunks=chunks,
        vectors=vectors,
    )
    return len(chunks)
