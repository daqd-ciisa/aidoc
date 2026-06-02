"""Recuperación RAG (híbrida: semántica + léxica) y contexto + citas."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.config import settings
from app.services import qdrant
from app.services.embeddings import get_embeddings

# Peso del componente léxico (palabras clave) sobre el score semántico. Permite
# recuperar tablas/datos OCR (ej. "IVA", "Total Neto") que la similitud
# semántica pura deja fuera del top-k.
_LEX_WEIGHT = 0.4
_STOPWORDS = {
    "cual", "cuales", "que", "como", "donde", "cuando", "cuanto", "cuantos",
    "cuanta", "cuantas", "los", "las", "del", "una", "uno", "unos", "unas",
    "para", "con", "por", "sus", "este", "esta", "estos", "estas", "the",
}


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _query_terms(query: str) -> set[str]:
    toks = re.findall(r"[a-z0-9]+", _normalize(query))
    return {t for t in toks if len(t) >= 3 and t not in _STOPWORDS}


@dataclass
class RetrievedChunk:
    document_id: str
    filename: str
    page: int | None
    chunk_index: int
    text: str
    score: float


SYSTEM_PROMPT = (
    "Eres AIDOC, un asistente que responde preguntas sobre los documentos del "
    "usuario.\n"
    "Reglas:\n"
    "- Respondé usando ÚNICAMENTE el CONTEXTO recuperado de los documentos.\n"
    "- Si la respuesta no está en el contexto, decí claramente que no encontrás "
    "esa información en los documentos.\n"
    "- Citá las fuentes con los marcadores [n] que aparecen en el contexto.\n"
    "- Respondé en el mismo idioma que el usuario.\n"
    "- Sé conciso y preciso."
)


def retrieve(
    query: str,
    tenant_id: str,
    document_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Recupera los chunks más relevantes con búsqueda HÍBRIDA (SÍNCRONO).

    Trae un pool amplio por similitud semántica y lo re-rankea sumando un boost
    léxico por coincidencia de palabras clave de la consulta (rescata tablas/OCR
    que el coseno puro deja fuera)."""
    k = top_k or settings.RETRIEVER_TOP_K
    vector = get_embeddings().embed_query(query)
    hits = qdrant.search(
        query_vector=vector,
        tenant_id=tenant_id,
        document_ids=document_ids,
        top_k=max(k * 4, 30),  # pool de candidatos para re-rankear
    )

    qterms = _query_terms(query)

    def blended(h: dict) -> float:
        if not qterms:
            return h["score"]
        words = set(re.findall(r"[a-z0-9]+", _normalize(h.get("text", ""))))
        lex = sum(1 for t in qterms if t in words) / len(qterms)
        return h["score"] + _LEX_WEIGHT * lex

    hits.sort(key=blended, reverse=True)
    return [
        RetrievedChunk(
            document_id=h["document_id"],
            filename=h["filename"],
            page=h["page"],
            chunk_index=h["chunk_index"],
            text=h["text"],
            score=h["score"],
        )
        for h in hits[:k]
    ]


def rank_documents(
    query: str,
    tenant_id: str,
    candidate_k: int = 40,
    top_docs: int = 3,
) -> list[dict]:
    """Busca por similitud y agrupa los hits POR DOCUMENTO, devolviendo los
    documentos más parecidos a ``query`` (SÍNCRONO).

    Cada documento se rankea por su mejor fragmento; ``hits`` cuenta cuántos
    fragmentos del documento entraron en los candidatos (señal de cobertura)."""
    vector = get_embeddings().embed_query(query)
    hits = qdrant.search(
        query_vector=vector, tenant_id=tenant_id, top_k=candidate_k
    )
    groups: dict[str, dict] = {}
    for h in hits:
        doc_id = h["document_id"]
        if doc_id is None:
            continue
        g = groups.get(doc_id)
        if g is None:
            groups[doc_id] = {
                "document_id": doc_id,
                "filename": h["filename"],
                "best_score": h["score"],
                "hits": 1,
                "snippet": h["text"][:300],
            }
        else:
            g["hits"] += 1
            if h["score"] > g["best_score"]:
                g["best_score"] = h["score"]
                g["snippet"] = h["text"][:300]
    ranked = sorted(groups.values(), key=lambda g: g["best_score"], reverse=True)
    return ranked[:top_docs]


def full_document_context(tenant_id: str, document_id: str) -> tuple[str, list[dict]]:
    """Arma el contexto con el documento COMPLETO (todos sus chunks ordenados).

    Devuelve ``(texto, chunks)``; ``chunks`` sirve para nombre/citas."""
    chunks = qdrant.get_document_chunks(
        tenant_id=tenant_id, document_id=document_id
    )
    parts: list[str] = []
    for c in chunks:
        loc = f" p.{c['page']}" if c.get("page") else ""
        parts.append(f"({c['filename']}{loc})\n{c['text']}")
    return "\n\n".join(parts), chunks


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Arma el bloque de CONTEXTO con marcadores [n] para citar."""
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        loc = c.filename + (f" p.{c.page}" if c.page else "")
        parts.append(f"[{i}] ({loc})\n{c.text}")
    return "\n\n---\n\n".join(parts)


def build_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    """Serializa las citas para el frontend."""
    return [
        {
            "ref": i,
            "document_id": c.document_id,
            "filename": c.filename,
            "page": c.page,
            "chunk_index": c.chunk_index,
            "snippet": c.text[:300],
            "score": round(c.score, 4),
        }
        for i, c in enumerate(chunks, start=1)
    ]
