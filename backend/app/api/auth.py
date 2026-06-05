"""Autenticación y administración de organizaciones/usuarios (provisionado por admin)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.models.organization import Organization
from app.db.models.user import ROLE_ADMIN, ROLE_MEMBER, ROLE_SUPERADMIN, User
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    organization_id: str | None
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class OrgCreate(BaseModel):
    name: str
    slug: str = Field(pattern=r"^[a-z0-9-]{2,64}$")
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class OrgRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = ROLE_MEMBER


# ─── Login / me ───────────────────────────────────────────────────────────────


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == req.email.lower()))
    if user is None or not user.is_active or not verify_password(
        req.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )
    token = create_access_token(sub=user.id, org=user.organization_id, role=user.role)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


# ─── Administración de organizaciones (super-admin) ─────────────────────────────


@router.post("/organizations")
async def create_organization(
    req: OrgCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(ROLE_SUPERADMIN)),
) -> OrgRead:
    """Crea una organización y su usuario admin inicial."""
    org = Organization(id=str(uuid.uuid4()), slug=req.slug, name=req.name)
    db.add(org)
    db.add(
        User(
            id=str(uuid.uuid4()),
            email=req.admin_email.lower(),
            password_hash=hash_password(req.admin_password),
            organization_id=org.id,
            role=ROLE_ADMIN,
            is_active=True,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El slug o el email del admin ya existen.",
        )
    await db.refresh(org)
    return OrgRead.model_validate(org)


@router.get("/organizations")
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(ROLE_SUPERADMIN)),
) -> list[OrgRead]:
    rows = await db.scalars(select(Organization).order_by(Organization.created_at.desc()))
    return [OrgRead.model_validate(o) for o in rows]


# ─── Administración de usuarios (admin de la org) ───────────────────────────────


@router.post("/users")
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(ROLE_ADMIN)),
) -> UserRead:
    """Un admin crea un usuario dentro de SU organización."""
    if req.role not in (ROLE_ADMIN, ROLE_MEMBER):
        raise HTTPException(status_code=422, detail="Rol inválido.")
    user = User(
        id=str(uuid.uuid4()),
        email=req.email.lower(),
        password_hash=hash_password(req.password),
        organization_id=admin.organization_id,
        role=req.role,
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El email ya existe."
        )
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(ROLE_ADMIN)),
) -> list[UserRead]:
    rows = await db.scalars(
        select(User)
        .where(User.organization_id == admin.organization_id)
        .order_by(User.created_at.desc())
    )
    return [UserRead.model_validate(u) for u in rows]
