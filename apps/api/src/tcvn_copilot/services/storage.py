"""S3-compatible object storage helpers.

Uses boto3 in async context via `asyncio.to_thread` to avoid pulling in a
heavyweight async-S3 dep. Streams uploads with a size cap.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config

from tcvn_copilot.config import get_settings
from tcvn_copilot.core.errors import DomainError
from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)

_client = None  # type: ignore[var-annotated]


def _s3():  # type: ignore[no-untyped-def]
    global _client  # noqa: PLW0603
    if _client is None:
        s = get_settings()
        _client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            region_name=s.s3_region,
            aws_access_key_id=s.s3_access_key.get_secret_value(),
            aws_secret_access_key=s.s3_secret_key.get_secret_value(),
            config=Config(signature_version="s3v4"),
        )
    return _client


async def upload_file(
    stream: BinaryIO,
    *,
    key: str,
    max_bytes: int,
    content_type: str,
    bucket: str | None = None,
) -> int:
    settings = get_settings()
    bucket = bucket or settings.s3_bucket_uploads

    # Stream in 8 MB chunks; abort if the cap is breached.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await asyncio.to_thread(stream.read, 8 * 1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DomainError(
                "upload exceeds maximum allowed size",
                details={"max_bytes": max_bytes},
            )
        chunks.append(chunk)

    body = b"".join(chunks)
    await asyncio.to_thread(
        _s3().put_object,
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return total


async def upload_bytes(
    data: bytes, *, key: str, content_type: str, bucket: str | None = None
) -> None:
    settings = get_settings()
    bucket = bucket or settings.s3_bucket_reports
    await asyncio.to_thread(
        _s3().put_object,
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )


async def download_to_path(key: str, dest: Path, *, bucket: str | None = None) -> None:
    settings = get_settings()
    bucket = bucket or settings.s3_bucket_uploads
    dest.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_s3().download_file, bucket, key, str(dest))


async def presigned_get_url(
    key: str, *, expires_in: int = 600, bucket: str | None = None
) -> str:
    settings = get_settings()
    bucket = bucket or settings.s3_bucket_reports
    url = await asyncio.to_thread(
        _s3().generate_presigned_url,
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return str(url)
