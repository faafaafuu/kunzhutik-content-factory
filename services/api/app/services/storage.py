from __future__ import annotations

from io import BytesIO

import boto3
from botocore.client import Config

from app.core.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_secure,
        config=Config(signature_version="s3v4"),
    )


def upload_bytes(key: str, content: bytes, mime_type: str) -> str:
    client = get_s3_client()
    client.upload_fileobj(
        Fileobj=BytesIO(content),
        Bucket=settings.s3_bucket,
        Key=key,
        ExtraArgs={"ContentType": mime_type},
    )
    return key


def download_bytes(key: str) -> bytes:
    client = get_s3_client()
    response = client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()


def get_public_asset_url(key: str) -> str:
    base = settings.app_base_url.rstrip("/")
    return f"{base}/api/v1/storage/{key}"
