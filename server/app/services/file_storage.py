"""
Where uploaded PDF files live.

In production they go to S3-compatible object storage (Backblaze B2,
Cloudflare R2, AWS S3...), because the free hosting tier wipes its local disk on
every restart and redeploy. When it isn't configured — local development and
tests — files go to UPLOAD_DIR.

`PdfDocument.storage_path` holds what `save_pdf` returned: an object key like
"<user_id>/<uuid>.pdf", or a local file path. Rows saved before object storage
was switched on keep their old local paths; those files are gone, so they read
as missing.
"""
import asyncio
import logging
import re
import shutil
import uuid
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def object_storage_enabled() -> bool:
    return bool(
        settings.S3_ENDPOINT_URL
        and settings.S3_ACCESS_KEY_ID
        and settings.S3_SECRET_ACCESS_KEY
        and settings.S3_BUCKET
    )


def describe() -> str:
    """One line for the startup log saying where PDFs will be stored."""
    if object_storage_enabled():
        if not re.fullmatch(r"https?://[^\s/]+/?", settings.S3_ENDPOINT_URL):
            return (
                f"INVALID S3_ENDPOINT_URL {settings.S3_ENDPOINT_URL!r} - it must be just "
                "the URL, like https://s3.us-east-005.backblazeb2.com; uploads will fail"
            )
        return f"object storage, bucket {settings.S3_BUCKET!r} at {settings.S3_ENDPOINT_URL}"
    names = ("S3_ENDPOINT_URL", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")
    missing = [name for name in names if not getattr(settings, name)]
    if len(missing) < len(names):
        return (
            f"LOCAL DISK ({settings.UPLOAD_DIR}) - object storage is half-configured, "
            f"missing: {', '.join(missing)}"
        )
    return f"local disk ({settings.UPLOAD_DIR}); set the S3_* variables to use object storage"


def _region() -> str:
    """Signing region. B2 needs the one in its endpoint; R2 accepts "auto"."""
    if settings.S3_REGION:
        return settings.S3_REGION
    # e.g. https://s3.us-west-004.backblazeb2.com -> us-west-004
    match = re.match(r"https?://s3\.([a-z0-9-]+)\.backblazeb2\.com", settings.S3_ENDPOINT_URL)
    return match.group(1) if match else "auto"


@lru_cache()
def _client():
    # Imported lazily: boto3 is only needed (and only costs memory) when enabled
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=_region(),
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _user_dir(user_id: uuid.UUID) -> Path:
    return Path(settings.UPLOAD_DIR) / str(user_id)


# --- Blocking implementations (run via asyncio.to_thread) ---------------------

def _save(user_id: uuid.UUID, content: bytes) -> str:
    name = f"{uuid.uuid4()}.pdf"
    if object_storage_enabled():
        key = f"{user_id}/{name}"
        _client().put_object(
            Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType="application/pdf"
        )
        return key
    path = _user_dir(user_id) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def _read(storage_path: str) -> bytes | None:
    if object_storage_enabled():
        client = _client()
        try:
            return client.get_object(Bucket=settings.S3_BUCKET, Key=storage_path)["Body"].read()
        except client.exceptions.NoSuchKey:
            return None
    try:
        return Path(storage_path).read_bytes()
    except FileNotFoundError:
        return None


def _delete(storage_path: str) -> None:
    if object_storage_enabled():
        # Deleting a missing key succeeds silently on S3-compatible stores
        _client().delete_object(Bucket=settings.S3_BUCKET, Key=storage_path)
        return
    Path(storage_path).unlink(missing_ok=True)


def _delete_user_files(user_id: uuid.UUID) -> None:
    if object_storage_enabled():
        client = _client()
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=f"{user_id}/"):
            keys = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if keys:
                client.delete_objects(Bucket=settings.S3_BUCKET, Delete={"Objects": keys})
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
