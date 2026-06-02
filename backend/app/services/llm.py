"""Cliente LLM de chat (NVIDIA NIM, API compatible OpenAI)."""
from __future__ import annotations

import httpx
from langchain_openai import ChatOpenAI

from app.config import settings


def get_chat_llm(
    *,
    temperature: float | None = None,
    streaming: bool = True,
    max_tokens: int | None = None,
) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_URL,
        api_key=settings.LLM_API_KEY,
        temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
        max_tokens=settings.LLM_MAX_TOKENS if max_tokens is None else max_tokens,
        streaming=streaming,
        http_client=httpx.Client(verify=settings.VERIFY_SSL),
        http_async_client=httpx.AsyncClient(verify=settings.VERIFY_SSL),
    )
