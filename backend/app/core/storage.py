from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.settings import settings


_client: Optional[Minio] = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=bool(settings.MINIO_SECURE),
        )
    return _client


def ensure_bucket() -> None:
    client = get_minio_client()
    bucket = settings.MINIO_BUCKET
    found = client.bucket_exists(bucket)
    if not found:
        client.make_bucket(bucket)


def put_text(object_key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
    if (settings.STORAGE_MODE or "minio").lower() == "local":
        base = settings.LOCAL_STORAGE_DIR
        if not base:
            raise RuntimeError("LOCAL_STORAGE_DIR is not set")
        # Treat object_key like an S3 key; store under LOCAL_STORAGE_DIR.
        target = Path(base) / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return

    client = get_minio_client()
    ensure_bucket()
    data = text.encode("utf-8")
    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def safe_put_text(object_key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> Optional[str]:
    try:
        put_text(object_key, text, content_type)
        return object_key
    except S3Error:
        return None
    except Exception:
        return None
