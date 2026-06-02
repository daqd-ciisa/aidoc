"""Conector de OneDrive / Microsoft Graph (importación puntual).

El frontend autentica con MSAL (popup, scope Files.Read), el usuario elige
archivos y acá los descargamos vía Microsoft Graph. Los archivos de OneDrive son
binarios reales (pdf/docx/...) → descarga directa, sin export como en Google.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from app.ingestion.parsers import SUPPORTED_EXTENSIONS

SOURCE_ONEDRIVE = "onedrive"

_GRAPH = "https://graph.microsoft.com/v1.0"


async def download_files(
    access_token: str, files: list[dict]
) -> tuple[list[tuple[str, bytes, str | None]], list[str], list[str]]:
    """Descarga los archivos elegidos por id de Graph.

    Devuelve (items, rechazados, fallidos)."""
    items: list[tuple[str, bytes, str | None]] = []
    rejected: list[str] = []
    failed: list[str] = []
    headers = {"Authorization": f"Bearer {access_token}"}

    # follow_redirects: el endpoint /content responde 302 a una URL prefirmada.
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for f in files:
            fid = f.get("id")
            name = f.get("name") or (fid or "documento")
            if not fid:
                failed.append(name)
                continue
            if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                rejected.append(name)
                continue
            try:
                resp = await client.get(
                    f"{_GRAPH}/me/drive/items/{fid}/content", headers=headers
                )
                resp.raise_for_status()
                ctype = resp.headers.get("content-type")
                items.append((name, resp.content, ctype))
            except Exception:  # noqa: BLE001
                failed.append(name)

    return items, rejected, failed
