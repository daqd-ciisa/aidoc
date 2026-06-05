"""Bootstrap del super-admin de plataforma desde variables de entorno.

Si ``SUPERADMIN_EMAIL`` y ``SUPERADMIN_PASSWORD`` están definidos y no existe aún
ese usuario, lo crea al arrancar. Idempotente y seguro de re-ejecutar.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.auth.security import hash_password
from app.config import settings
from app.db.models.user import ROLE_SUPERADMIN, User
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("aidoc.auth")


async def ensure_superadmin() -> None:
    if not (settings.SUPERADMIN_EMAIL and settings.SUPERADMIN_PASSWORD):
        return
    email = settings.SUPERADMIN_EMAIL.lower()
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            return
        db.add(
            User(
                id=str(uuid.uuid4()),
                email=email,
                password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                organization_id=None,
                role=ROLE_SUPERADMIN,
                is_active=True,
            )
        )
        await db.commit()
        logger.info("Super-admin creado: %s", email)
