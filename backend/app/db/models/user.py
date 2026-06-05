"""Usuario de la plataforma (auth + pertenencia a una organización/tenant)."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, UUIDMixin

# Roles posibles.
ROLE_SUPERADMIN = "superadmin"  # gestiona organizaciones; no pertenece a ninguna
ROLE_ADMIN = "admin"            # administra usuarios de SU organización + usa la app
ROLE_MEMBER = "member"          # usa la app dentro de su organización


class User(UUIDMixin, TimestampMixin, Base):
    """Usuario. Su ``organization_id`` es el tenant cuyos datos puede ver.

    El super-admin no tiene organización (``organization_id`` nulo) y solo opera
    sobre los endpoints de administración.
    """

    __tablename__ = "app_user"  # "user" es palabra reservada en Postgres

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=ROLE_MEMBER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
