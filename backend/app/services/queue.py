"""Cola de tareas (ARQ sobre Redis) para encolar indexado desde la API."""
from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _pool


async def enqueue_index(document_id: str) -> str | None:
    """Encola el indexado de un documento. Devuelve el job_id de ARQ."""
    pool = await get_arq_pool()
    job = await pool.enqueue_job("index_document", document_id)
    return job.job_id if job else None
