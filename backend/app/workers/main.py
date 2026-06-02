"""WorkerSettings de ARQ. Ejecutar: ``arq app.workers.main.WorkerSettings``."""
from __future__ import annotations

from arq.connections import RedisSettings

from app.config import settings
from app.services import storage
from app.services.qdrant import ensure_collection
from app.workers.tasks import index_document


async def startup(ctx: dict) -> None:
    ensure_collection()
    storage.ensure_bucket()


class WorkerSettings:
    functions = [index_document]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    max_jobs = settings.BATCH_WORKERS
