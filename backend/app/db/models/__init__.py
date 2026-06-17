"""Registro de modelos ORM.

Importar acá cada modelo para que Alembic los detecte vía ``Base.metadata``.
"""
from app.db.models.approved_url import ApprovedUrl
from app.db.models.chat import ChatMessage, ChatSession, MessageRole
from app.db.models.document import Document, DocumentStatus
from app.db.models.organization import Organization
from app.db.models.quote import Quote
from app.db.models.user import User

__all__ = [
    "Organization",
    "User",
    "Document",
    "DocumentStatus",
    "ChatSession",
    "ChatMessage",
    "MessageRole",
    "Quote",
    "ApprovedUrl",
]
