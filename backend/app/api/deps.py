"""Dependencies compartidas de la API: autenticación y tenant."""
from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decodifica el JWT del header ``Authorization: Bearer`` y carga el usuario."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    user = await db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido"
        )
    return user


async def get_tenant_id(user: User = Depends(get_current_user)) -> str:
    """Tenant del usuario autenticado (= su ``organization_id``).

    Reemplaza al stub single-tenant: ahora cada request queda aislado por la
    organización del usuario. El super-admin (sin org) no puede usar endpoints
    de datos; debe operar sobre los de administración.
    """
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no pertenece a una organización.",
        )
    return user.organization_id


def require_role(
    *roles: str,
) -> Callable[..., Coroutine[Any, Any, User]]:
    """Dependency factory: exige que el usuario tenga uno de los roles dados."""

    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para esta operación.",
            )
        return user

    return _dep
