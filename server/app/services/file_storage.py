"""
Where uploaded PDF files live.

In production they go to Cloudflare R2 (S3-compatible object storage), because
the free hosting tier wipes its local disk on every restart and redeploy. When
R2 isn't configured — local development and tests — files go to UPLOAD_DIR.

`PdfDocument.storage_path` holds what `save_pdf` returned: an R2 object key
like "<user_id>/<uuid>.pdf", or a local file path. Rows saved before R2 was
switched on keep their old local paths; those files are gone, so they read as
missing.
"""
import asyncio
import logging
import shutil
import uuid
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def r2_enabled() -> bool:
    return bool(
        settings.R2_ACCOUNT_ID
        and settings.R2_ACCESS_KEY_ID
        and settings.R2_SECRET_ACCESS_KEY
        and settings.R2_BUCKET
    )


@lru_cache()
def _r2_client():
    # Imported lazily: boto3 is only needed (and only costs memory) with R2 on
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _user_dir(user_id: uuid.UUID) -> Path:
    return Path(settings.UPLOAD_DIR) / str(user_id)


# --- Blocking implementations (run via asyncio.to_thread) ---------------------

def _save(user_id: uuid.UUID, content: bytes) -> str:
    name = f"{uuid.uuid4()}.pdf"
    if r2_enabled():
        key = f"{user_id}/{name}"
        _r2_client().put_object(
            Bucket=settings.R2_BUCKET, Key=key, Body=content, ContentType="application/pdf"
        )
        return key
    path = _user_dir(user_id) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def _read(storage_path: str) -> bytes | None:
    if r2_enabled():
        client = _r2_client()
        try:
            return client.get_object(Bucket=settings.R2_BUCKET, Key=storage_path)["Body"].read()
        except client.exceptions.NoSuchKey:
            return None
    try:
        return Path(storage_path).read_bytes()
    except FileNotFoundError:
        return None


def _delete(storage_path: str) -> None:
    if r2_enabled():
        # Deleting a missing key succeeds silently on S3/R2
        _r2_client().delete_object(Bucket=settings.R2_BUCKET, Key=storage_path)
        return
    Path(storage_path).unlink(missing_ok=True)


def _delete_user_files(user_id: uuid.UUID) -> None:
    if r2_enabled():
        client = _r2_client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.R2_BUCKET, Prefix=f"{user_id}/"):
            keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if keys:
                client.delete_objects(Bucket=settings.R2_BUCKET, Delete={"Objects": keys})
        return
    shutil.rmtree(_user_dir(user_id), ignore_errors=True)


# --- Async API ---------------------------------------------------------------

async def save_pdf(user_id: uuid.UUID, content: bytes) -> str:
    """Store a PDF and return the value to keep in `storage_path`."""
    return await asyncio.to_thread(_save, user_id, content)


async def read_pdf(storage_path: str) -> bytes | None:
    """The PDF's bytes, or None if the file no longer exists."""
    return await asyncio.to_thread(_read, storage_path)


async def delete_pdf_file(storage_path: str) -> None:
    """Remove one stored PDF. Failures are logged, not raised."""
    try:
        await asyncio.to_thread(_delete, storage_path)
    except Exception:
        logger.exception("Could not delete stored file %s", storage_path)


async def delete_user_files(user_id: uuid.UUID) -> None:
    """Remove every stored PDF of one user. Failures are logged, not raised."""
    try:
        await asyncio.to_thread(_delete_user_files, user_id)
    except Exception:
        logger.exception("Could not delete stored files of user %s", user_id)
