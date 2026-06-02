"""Mixins compartidos por todos los modelos custom."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """PK UUID como string (portable entre motores)."""

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Toda tabla custom lleva ``tenant_id`` indexado.

    Single-tenant hoy (todo cae en el tenant ``default``); el día que activemos
    multi-tenant solo hay que empezar a filtrar por esta columna — sin migración
    de esquema. Mismo patrón que onyx-bi.
    """

    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )
