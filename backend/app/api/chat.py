"""Chat RAG con streaming SSE + gestión de sesiones."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.chat import rag
from app.db.models.chat import ChatMessage, ChatSession, MessageRole
from app.db.session import AsyncSessionLocal, get_db
from app.services.llm import get_chat_llm

logger = logging.getLogger("aidoc.chat")

router = APIRouter(prefix="/chat", tags=["chat"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    document_ids: list[str] | None = None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    citations: list | None
    created_at: datetime


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionRead):
    messages: list[MessageRead]


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _sse(event: str, data: dict | list) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _get_session(
    db: AsyncSession, tenant_id: str, session_id: str
) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None or session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return session


# ─── Streaming endpoint ───────────────────────────────────────────────────────


async def _chat_stream(
    tenant_id: str, req: ChatRequest
) -> AsyncGenerator[str, None]:
    async with AsyncSessionLocal() as db:
        # 1. Cargar o crear la sesión.
        if req.session_id:
            session = await db.get(ChatSession, req.session_id)
            if session is None or session.tenant_id != tenant_id:
                yield _sse("error", {"detail": "Sesión no encontrada"})
                return
        else:
            session = ChatSession(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title=req.message[:60] or "Nueva conversación",
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        # 2. Historial previo (antes de agregar el mensaje actual).
        history = list(
            await db.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at.asc())
            )
        )

        # 3. Persistir el mensaje del usuario.
        db.add(
            ChatMessage(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                session_id=session.id,
                role=MessageRole.USER.value,
                content=req.message,
            )
        )
        await db.commit()

        yield _sse("meta", {"session_id": session.id})

        # 4. Recuperación RAG (embedding es síncrono → thread).
        try:
            chunks = await asyncio.to_thread(
                rag.retrieve, req.message, tenant_id, req.document_ids
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallo en recuperación RAG")
            yield _sse("error", {"detail": f"Recuperación falló: {exc}"})
            return

        citations = rag.build_citations(chunks)
        yield _sse("citations", citations)

        # 5. Armar mensajes para el LLM.
        messages = [SystemMessage(content=rag.SYSTEM_PROMPT)]
        for m in history:
            if m.role == MessageRole.USER.value:
                messages.append(HumanMessage(content=m.content))
            else:
                messages.append(AIMessage(content=m.content))
        context = rag.build_context(chunks)
        user_turn = req.message
        if context:
            user_turn = f"{req.message}\n\nCONTEXTO:\n{context}"
        messages.append(HumanMessage(content=user_turn))

        # 6. Stream de la respuesta.
        answer = ""
        try:
            llm = get_chat_llm(streaming=True)
            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    answer += token
                    yield _sse("token", {"text": token})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fallo en generación LLM")
            yield _sse("error", {"detail": f"Generación falló: {exc}"})
            return

        # 7. Persistir la respuesta del asistente.
        db.add(
            ChatMessage(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                session_id=session.id,
                role=MessageRole.ASSISTANT.value,
                content=answer,
                citations=citations,
            )
        )
        await db.commit()

        yield _sse("done", {"session_id": session.id})


@router.post("")
async def chat(
    req: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> StreamingResponse:
    return StreamingResponse(
        _chat_stream(tenant_id, req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Sesiones ─────────────────────────────────────────────────────────────────


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> list[SessionRead]:
    rows = await db.scalars(
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return [SessionRead.model_validate(s) for s in rows]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> SessionDetail:
    session = await _get_session(db, tenant_id, session_id)
    messages = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    return SessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageRead.model_validate(m) for m in messages],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    session = await _get_session(db, tenant_id, session_id)
    await db.delete(session)
    await db.commit()
    return Response(status_code=204)
