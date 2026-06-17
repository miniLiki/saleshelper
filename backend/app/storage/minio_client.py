from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


class ObjectStorage:
    def __init__(self, client: Minio | None = None):
        self.client = client or get_minio_client()

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(settings.minio_bucket):
            self.client.make_bucket(settings.minio_bucket)

    def put_bytes(self, object_name: str, data: bytes, content_type: str | None = None) -> None:
        self.ensure_bucket()
        self.client.put_object(
            settings.minio_bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )

    def get_bytes(self, object_name: str) -> bytes:
        response = self.client.get_object(settings.minio_bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def health(self) -> bool:
        try:
            self.client.bucket_exists(settings.minio_bucket)
            return True
        except S3Error:
            return False
