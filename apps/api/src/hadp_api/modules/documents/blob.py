"""Object storage abstraction (S3-compatible).

Production/dev use MinIO/S3 (private bucket, EU region, short-lived signed access). Tests
use an in-process fake so they do not depend on a running object store. Source files are
stored before parsing and addressed by content (tenant/patient/checksum).
"""

from __future__ import annotations

from typing import Protocol

from hadp_api.config import Settings


class BlobStore(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


class InMemoryBlobStore:
    """Process-local fake for tests. Not for production use."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._store[key] = data

    def get(self, key: str) -> bytes:
        return self._store[key]

    def exists(self, key: str) -> bool:
        return key in self._store


class S3BlobStore:
    """S3-compatible store (MinIO locally, EU-region bucket in production)."""

    def __init__(self, settings: Settings) -> None:
        import boto3

        self._bucket = settings.s3_bucket_source_documents
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        body: bytes = resp["Body"].read()
        return body

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False


_in_memory_singleton: InMemoryBlobStore | None = None


def get_blob_store(settings: Settings) -> BlobStore:
    # Tests run against a process-local fake so they never require MinIO.
    if settings.app_env == "test":
        global _in_memory_singleton
        if _in_memory_singleton is None:
            _in_memory_singleton = InMemoryBlobStore()
        return _in_memory_singleton
    return S3BlobStore(settings)
