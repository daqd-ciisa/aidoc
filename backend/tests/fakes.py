"""Dobles de prueba (fakes) de los servicios remotos de PCAI.

La Capa 1 (E2E de "plumbing") ejercita TODO el pipeline real —upload → MinIO →
parse → chunk → Qdrant → retrieve → chat → cotización → PDF— pero reemplaza los
dos únicos servicios que viven fuera del proceso y que dependen de PCAI:

  • embeddings (NVIDIA NIM) → ``FakeEmbeddings``: vector determinista de 1024 dims.
  • LLM de chat (NVIDIA NIM) → ``FakeChatLLM``: respuestas predefinidas según la
    tarea (chat, extracción de cotización, resumen al indexar, rerank).

Así los tests corren en CI sin tokens ni red, y las aserciones son ESTRUCTURALES
(no validan calidad del modelo, eso es la Capa 2 contra PCAI real).
"""
from __future__ import annotations

import hashlib
import json
import random

from app.config import settings


# ── Embeddings ──────────────────────────────────────────────────────────────────


class FakeEmbeddings:
    """Embeddings deterministas: mismo texto → mismo vector (semilla = hash).

    Reproduce la interfaz de ``langchain_openai.OpenAIEmbeddings`` que usa el código
    (``embed_query`` / ``embed_documents``). La dimensión coincide con la colección
    real de Qdrant (``settings.EMBED_DIMENSIONS`` = 1024).
    """

    def _vec(self, text: str) -> list[float]:
        seed = int.from_bytes(
            hashlib.sha256((text or "x").encode()).digest()[:8], "big"
        )
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(settings.EMBED_DIMENSIONS)]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


# ── LLM de chat ─────────────────────────────────────────────────────────────────


class _Resp:
    """Imita el objeto de respuesta de langchain (tiene ``.content``)."""

    def __init__(self, content: str) -> None:
        self.content = content


# Respuestas canónicas por tarea. El JSON valida contra los schemas reales
# (QuoteDraft / DocumentSummary) y el parser tolerante del código lo acepta tal cual.
_QUOTE_JSON = json.dumps(
    {
        "cliente": "ACME",
        "moneda": "MXN",
        "items": [
            {
                "servicio": "Soporte técnico",
                "descripcion": "Soporte mensual",
                "cantidad": 1,
                "precio_unitario": 1000,
                "importe": 1000,
            }
        ],
        "subtotal": 1000,
        "impuestos": 160,
        "total": 1160,
        "vigencia": "30 días",
        "condiciones": "Pago a 30 días",
        "notas": "Borrador de prueba generado por FakeChatLLM",
        "no_encontrado": [],
    }
)

_SUMMARY_JSON = json.dumps(
    {
        "categoria": "servicio",
        "tipo": "servicio de soporte técnico",
        "cliente": "ACME",
        "objeto": "Servicio de soporte técnico mensual",
        "servicios": ["soporte técnico"],
        "moneda": "MXN",
        "monto_total": 1000,
        "resumen": "Cotización de soporte técnico para ACME.",
    }
)

_RERANK_JSON = json.dumps(
    {"precedentes": [{"id": 0, "afinidad": 95, "motivo": "Coincide con el pedido."}]}
)


class FakeChatLLM:
    """LLM falso que devuelve respuestas predefinidas según el system prompt.

    Cubre los tres modos en que el código invoca al modelo:
      • ``astream`` → chat RAG (streaming token a token).
      • ``ainvoke`` → extracción de cotización y rerank de precedentes.
      • ``invoke``  → resumen del documento al indexar (síncrono).
    """

    @staticmethod
    def _system(messages: list) -> str:
        for m in messages:
            return getattr(m, "content", "") or ""
        return ""

    def _canned(self, messages: list) -> str:
        system = self._system(messages)
        if "ayuda a elegir" in system:  # _RERANK_SYSTEM
            return _RERANK_JSON
        if "clasifica propuestas" in system:  # _SUMMARY_SYSTEM
            return _SUMMARY_JSON
        return _QUOTE_JSON  # EXTRACTION / GUIDED / SCRATCH

    # Síncrono (summarizer.summarize_document).
    def invoke(self, messages: list) -> _Resp:
        return _Resp(self._canned(messages))

    # Async no-streaming (extractor, rerank, proposal).
    async def ainvoke(self, messages: list) -> _Resp:
        return _Resp(self._canned(messages))

    # Async streaming (chat RAG). Emite una respuesta con una cita [1].
    async def astream(self, messages: list):
        for token in ("Según ", "el documento, ", "el servicio cuesta 1000 MXN ", "[1]."):
            yield _Resp(token)
