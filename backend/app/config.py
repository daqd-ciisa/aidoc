"""Configuración central de AIDOC (reusa el Settings del prototipo Streamlit)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ──
    APP_NAME: str = "AIDOC"
    ENVIRONMENT: str = "development"
    DEFAULT_TENANT_ID: str = "default"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Postgres ──
    DATABASE_URL: str = "postgresql+asyncpg://aidoc:aidoc@localhost:5432/aidoc"

    # ── Redis (cola de indexado async) ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ──
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "aidoc_documents"
    QDRANT_API_KEY: str = ""

    # ── Object storage (S3 / MinIO) ──
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "aidoc"
    S3_SECRET_KEY: str = "aidoc-secret"
    S3_BUCKET: str = "aidoc-documents"
    S3_REGION: str = "us-east-1"

    # ── LLM (NVIDIA NIM en HPE PCAI) ──
    LLM_URL: str = (
        "https://llm-qwen3-30b-042026.project-pyxiia-proyectos."
        "serving.ai-application.ciisagl.local/v1"
    )
    LLM_API_KEY: str = "placeholder-llm-key"
    LLM_MODEL: str = "Qwen/Qwen3-30B-A3B-Instruct-2507-FP8"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # ── Embeddings ──
    EMBEDDINGS_URL: str = (
        "https://emb-qwen3-06b.project-user-jmartinez."
        "serving.ai-application.ciisagl.local/v1"
    )
    EMBEDDINGS_API_KEY: str = "placeholder-emb-key"
    EMBED_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"
    EMBED_DIMENSIONS: int = 1024

    # ── Ingesta / RAG ──
    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 200
    RETRIEVER_TOP_K: int = 8
    BATCH_WORKERS: int = 4

    # ── SSL (certs self-signed en PCAI) ──
    VERIFY_SSL: bool = False

    # ── Auth (Fase 4) ──
    SECRET_KEY: str = "change-me-in-prod-min-32-chars-please-rotate"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 h
    # Bootstrap del super-admin de plataforma (se crea al arrancar si no existe).
    SUPERADMIN_EMAIL: str = ""
    SUPERADMIN_PASSWORD: str = ""

    @property
    def sync_database_url(self) -> str:
        """URL síncrona para Alembic (psycopg2 en lugar de asyncpg)."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
