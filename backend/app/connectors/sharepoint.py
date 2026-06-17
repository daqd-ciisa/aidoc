"""Conector de SharePoint / Microsoft Graph (importación puntual).

Análogo a OneDrive (mismo Graph + MSAL), pero la jerarquía es
sitio → biblioteca de documentos (drive) → carpetas, así que cada archivo
elegido viaja con su ``site_id`` + ``drive_id``. Los archivos son binarios
reales (pdf/docx/...) → descarga directa por ``/content`` (302 a URL
prefirmada, igual que OneDrive).

Permiso de Graph necesario: ``Sites.Read.All`` (delegado) — normalmente
requiere consentimiento del admin del tenant de Azure AD.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from app.ingestion.parsers import SUPPORTED_EXTENSIONS

SOURCE_SHAREPOINT = "sharepoint"

_GRAPH = "https://graph.microsoft.com/v1.0"


async def download_files(
    access_token: str, files: list[dict]
) -> tuple[list[tuple[str, bytes, str | None]], list[str], list[str]]:
    """Descarga los archivos elegidos por (site_id, drive_id, item_id) de Graph.

    Devuelve (items, rechazados, fallidos)."""
    items: list[tuple[str, bytes, str | None]] = []
    rejected: list[str] = []
    failed: list[str] = []
    headers = {"Authorization": f"Bearer {access_token}"}

    # follow_redirects: el endpoint /content responde 302 a una URL prefirmada.
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for f in files:
            fid = f.get("id")
            site_id = f.get("site_id")
            drive_id = f.get("drive_id")
            name = f.get("name") or (fid or "documento")
            if not fid or not site_id or not drive_id:
                failed.append(name)
                continue
            if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                rejected.append(name)
                continue
            try:
                resp = await client.get(
                    f"{_GRAPH}/sites/{site_id}/drives/{drive_id}/items/{fid}/content",
                    headers=headers,
                )
                resp.raise_for_status()
                ctype = resp.headers.get("content-type")
                items.append((name, resp.content, ctype))
            except Exception:  # noqa: BLE001
                failed.append(name)

    return items, rejected, failed
