"""Cliente de embeddings (NVIDIA NIM, API compatible OpenAI)."""
from __future__ import annotations

import httpx
from langchain_openai import OpenAIEmbeddings

from app.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.EMBEDDINGS_URL,
        api_key=settings.EMBEDDINGS_API_KEY,
        http_client=httpx.Client(verify=settings.VERIFY_SSL),
        http_async_client=httpx.AsyncClient(verify=settings.VERIFY_SSL),
    )
