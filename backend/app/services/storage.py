"""Storage de archivos originales sobre S3 / MinIO (boto3, síncrono)."""
from __future__ import annotations

import boto3
from botocore.client import Config

from app.config import settings

_client = None


def get_s3():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
            verify=settings.VERIFY_SSL,
        )
    return _client


def ensure_bucket() -> None:
    """Crea el bucket si no existe (idempotente)."""
    s3 = get_s3()
    existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if settings.S3_BUCKET not in existing:
        s3.create_bucket(Bucket=settings.S3_BUCKET)


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> None:
    extra = {"ContentType": content_type} if content_type else {}
    get_s3().put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data, **extra)


def download_bytes(key: str) -> bytes:
    obj = get_s3().get_object(Bucket=settings.S3_BUCKET, Key=key)
    return obj["Body"].read()


def delete_object(key: str) -> None:
    get_s3().delete_object(Bucket=settings.S3_BUCKET, Key=key)
