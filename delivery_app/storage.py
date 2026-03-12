"""Object storage adapters for delivery photos."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Dict


@dataclass
class StoredObject:
    content: BytesIO
    content_type: str
    content_length: int


class S3Storage:
    """Upload and download delivery photos from S3-compatible storage."""

    def __init__(self, endpoint: str, bucket: str, access_key_id: str, secret_access_key: str, region: str):
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key_id or None,
            aws_secret_access_key=secret_access_key or None,
            region_name=region or None,
        )

    def upload_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=payload,
            ContentType=content_type,
        )

    def read_bytes(self, object_key: str) -> StoredObject:
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        body = response["Body"].read()
        return StoredObject(
            content=BytesIO(body),
            content_type=response.get("ContentType", "application/octet-stream"),
            content_length=len(body),
        )


class NullStorage:
    """Fallback storage used when S3 is not configured in the local environment."""

    def upload_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None:
        raise RuntimeError("S3 storage is not configured")

    def read_bytes(self, object_key: str) -> StoredObject:
        raise RuntimeError("S3 storage is not configured")


class InMemoryStorage:
    """Test storage backend."""

    def __init__(self):
        self.objects: Dict[str, Dict[str, bytes]] = {}

    def upload_bytes(self, *, object_key: str, payload: bytes, content_type: str) -> None:
        self.objects[object_key] = {"payload": payload, "content_type": content_type.encode("utf-8")}

    def read_bytes(self, object_key: str) -> StoredObject:
        item = self.objects[object_key]
        payload = item["payload"]
        return StoredObject(
            content=BytesIO(payload),
            content_type=item["content_type"].decode("utf-8"),
            content_length=len(payload),
        )
