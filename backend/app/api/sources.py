"""Endpoints de URLs aprobadas (fuentes consultadas EN VIVO en la validación)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.models.approved_url import ApprovedUrl
from app.db.session import get_db

router = APIRouter(prefix="/sources", tags=["sources"])


class ApprovedUrlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    label: str | None
    created_at: datetime


class ApprovedUrlCreate(BaseModel):
    url: str
    label: str | None = None


@router.get("/urls")
async def list_urls(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> list[ApprovedUrlRead]:
    rows = await db.scalars(
        select(ApprovedUrl)
        .where(ApprovedUrl.tenant_id == tenant_id)
        .order_by(ApprovedUrl.created_at.desc())
    )
    return [ApprovedUrlRead.model_validate(r) for r in rows]


@router.post("/urls")
async def add_url(
    req: ApprovedUrlCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ApprovedUrlRead:
    url = req.url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail="La URL debe empezar con http(s)://")

    # Dedup por (tenant, url).
    existing = await db.scalar(
        select(ApprovedUrl).where(
            ApprovedUrl.tenant_id == tenant_id, ApprovedUrl.url == url
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Esa URL ya está en la lista.")

    row = ApprovedUrl(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        url=url,
        label=(req.label or "").strip() or None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ApprovedUrlRead.model_validate(row)


@router.delete("/urls/{url_id}")
async def delete_url(
    url_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> Response:
    row = await db.get(ApprovedUrl, url_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="URL no encontrada")
    await db.delete(row)
    await db.commit()
    return Response(status_code=204)
