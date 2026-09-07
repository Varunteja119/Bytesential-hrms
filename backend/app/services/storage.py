from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config.settings import settings
from app.core.exceptions import AppError


class StorageClient(Protocol):
    def upload(self, key: str, data: bytes, content_type: str) -> None: ...
    def download(self, key: str) -> bytes: ...


class MinIOStorageClient:
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self._client = boto3.client("s3", endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except (BotoCoreError, ClientError):
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except (BotoCoreError, ClientError) as exc:
                raise AppError(f"Could not reach or create storage bucket: {exc}", status_code=502) from exc

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise AppError(f"Resume upload failed: {exc}", status_code=502) from exc

    def download(self, key: str) -> bytes:
        try:
            return self._client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except (BotoCoreError, ClientError) as exc:
            raise AppError(f"Resume download failed: {exc}", status_code=502) from exc


def get_storage_client() -> StorageClient:
    return MinIOStorageClient(
        endpoint_url=settings.minio_endpoint_url,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket_resumes,
    )
