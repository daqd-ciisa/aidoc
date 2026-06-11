"""Cliente Qdrant: colección, upsert de chunks, borrado y búsqueda por tenant."""
from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
        verify=settings.VERIFY_SSL,
        prefer_grpc=False,
    )


def ensure_collection() -> None:
    """Crea la colección y los índices de payload si no existen (idempotente)."""
    client = get_qdrant_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBED_DIMENSIONS, distance=Distance.COSINE
            ),
        )

    # Índices de payload para filtrar eficiente por tenant y documento.
    from qdrant_client.models import PayloadSchemaType

    for field in ("tenant_id", "document_id", "kind", "doc_type"):
        try:
            client.create_payload_index(
                settings.QDRANT_COLLECTION, field, PayloadSchemaType.KEYWORD
            )
        except Exception:  # noqa: BLE001 — ya existe o aún no está lista la colección
            pass


def upsert_chunks(
    *,
    tenant_id: str,
    document_id: str,
    filename: str,
    chunks: list[Any],
    vectors: list[list[float]],
    doc_type: str = "document",
) -> None:
    """Sube los vectores de los chunks de un documento.

    Cada ``chunk`` debe exponer ``.text``, ``.chunk_index`` y ``.page``.
    ``doc_type`` (``"document"``/``"catalog"``) viaja en el payload para poder
    filtrar el material de referencia al generar cotizaciones.
    """
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "tenant_id": tenant_id,
                "document_id": document_id,
                "filename": filename,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "kind": "chunk",
                "doc_type": doc_type,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    if points:
        get_qdrant_client().upsert(
            collection_name=settings.QDRANT_COLLECTION, points=points
        )


def upsert_summary(
    *,
    tenant_id: str,
    document_id: str,
    filename: str,
    vector: list[float],
    summary_text: str,
    summary: dict,
) -> None:
    """Sube UN punto ``kind="summary"`` por documento: vector de su resumen de alta
    señal + el resumen estructurado en el payload. Lo usa la búsqueda de precedentes
    (un vector representativo por documento, sin el ruido del boilerplate)."""
    get_qdrant_client().upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "tenant_id": tenant_id,
                    "document_id": document_id,
                    "filename": filename,
                    "text": summary_text,
                    "summary": summary,
                    "kind": "summary",
                },
            )
        ],
    )


def search(
    *,
    query_vector: list[float],
    tenant_id: str,
    document_ids: list[str] | None = None,
    top_k: int = 8,
    kind: str | None = None,
    doc_type: str | None = None,
) -> list[dict]:
    """Busca los puntos más relevantes, aislados por tenant.

    Si ``document_ids`` viene dado, restringe a esos documentos. ``kind`` filtra por
    tipo de punto: ``"summary"`` para la búsqueda de precedentes (un vector por
    documento); por defecto (``None``) busca contenido y EXCLUYE los resúmenes.
    ``doc_type`` restringe a una naturaleza de documento (ej. ``"catalog"`` para el
    material de referencia de cotizaciones).
    """
    must = [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    if document_ids:
        must.append(
            FieldCondition(key="document_id", match=MatchAny(any=document_ids))
        )
    if doc_type is not None:
        must.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))
    must_not = None
    if kind is not None:
        must.append(FieldCondition(key="kind", match=MatchValue(value=kind)))
    else:
        # Búsqueda de contenido: excluir los puntos de resumen (tolerante con
        # puntos viejos sin el campo "kind", que sí deben matchear).
        must_not = [FieldCondition(key="kind", match=MatchValue(value="summary"))]

    results = get_qdrant_client().search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(must=must, must_not=must_not),
        limit=top_k,
        with_payload=True,
    )
    out: list[dict] = []
    for r in results:
        p = r.payload or {}
        out.append(
            {
                "document_id": p.get("document_id"),
                "filename": p.get("filename"),
                "page": p.get("page"),
                "chunk_index": p.get("chunk_index"),
                "text": p.get("text", ""),
                "summary": p.get("summary"),
                "score": r.score,
            }
        )
    return out


def get_document_chunks(*, tenant_id: str, document_id: str) -> list[dict]:
    """Devuelve TODOS los chunks de un documento, ordenados por ``chunk_index``.

    Se usa para alimentar el precedente completo al generador guiado (no basta
    con los fragmentos difusos de ``search``)."""
    points, _ = get_qdrant_client().scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                FieldCondition(
                    key="document_id", match=MatchValue(value=document_id)
                ),
            ],
            # No incluir el punto de resumen en el contexto del documento completo.
            must_not=[FieldCondition(key="kind", match=MatchValue(value="summary"))],
        ),
        limit=2000,
        with_payload=True,
        with_vectors=False,
    )
    out: list[dict] = []
    for p in points:
        pl = p.payload or {}
        out.append(
            {
                "document_id": pl.get("document_id"),
                "filename": pl.get("filename"),
                "page": pl.get("page"),
                "chunk_index": pl.get("chunk_index", 0),
                "text": pl.get("text", ""),
            }
        )
    out.sort(key=lambda c: c["chunk_index"])
    return out


def delete_document_points(document_id: str) -> None:
    """Borra todos los vectores de un documento (reindex-safe / borrado)."""
    get_qdrant_client().delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id", match=MatchValue(value=document_id)
                )
            ]
        ),
    )
