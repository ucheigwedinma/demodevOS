
"""Backblaze B2 client via boto3 S3-compatible API."""

import logging
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

from django.conf import settings

logger = logging.getLogger(__name__)


def get_b2_client():
    """Return a configured boto3 S3 client pointing at B2."""
    return boto3.client(
        "s3",
        endpoint_url=settings.B2_ENDPOINT,
        aws_access_key_id=settings.B2_KEY_ID,
        aws_secret_access_key=settings.B2_APP_KEY,
        config=BotoConfig(signature_version="s3v4"),
    )


def upload_file(local_path: str | Path, b2_key: str) -> int:
    """Upload a local file to B2. Returns file size in bytes."""
    local_path = Path(local_path)
    size = local_path.stat().st_size
    client = get_b2_client()
    client.upload_file(
        str(local_path),
        settings.B2_BUCKET_NAME,
        b2_key,
    )
    logger.info("b2.upload key=%s size=%d", b2_key, size)
    return size


def upload_fileobj(fileobj, b2_key: str) -> None:
    """Upload a file-like object to B2."""
    client = get_b2_client()
    client.upload_fileobj(fileobj, settings.B2_BUCKET_NAME, b2_key)
    logger.info("b2.upload_fileobj key=%s", b2_key)


def list_objects(prefix: str) -> list[dict]:
    """List objects under a prefix. Returns list of {Key, Size, LastModified}."""
    client = get_b2_client()
    objects = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.B2_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            objects.append({
                "Key": obj["Key"],
                "Size": obj["Size"],
                "LastModified": obj["LastModified"],
            })
    return objects


def download_file(b2_key: str, local_path: str | Path) -> None:
    """Download a file from B2 to local path."""
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client = get_b2_client()
    client.download_file(settings.B2_BUCKET_NAME, b2_key, str(local_path))
    logger.info("b2.download key=%s -> %s", b2_key, local_path)


def delete_object(b2_key: str) -> None:
    """Delete an object from B2."""
    client = get_b2_client()
    client.delete_object(Bucket=settings.B2_BUCKET_NAME, Key=b2_key)
    logger.info("b2.delete key=%s", b2_key)


def head_object(b2_key: str) -> dict | None:
    """Get object metadata. Returns None if object doesn't exist."""
    client = get_b2_client()
    try:
        return client.head_object(Bucket=settings.B2_BUCKET_NAME, Key=b2_key)
    except client.exceptions.ClientError:
        return None
