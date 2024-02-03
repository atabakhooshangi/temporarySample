from django.db import models
from django_redis import get_redis_connection

from core.choice_field_types import BucketTypeChoices
from media.minio import MinioConnect


class Media(models.Model):
    key = models.CharField(
        verbose_name="Key",
        max_length=200,
        blank=False
    )
    bucket = models.CharField(
        verbose_name="Bucket",
        max_length=64,
        blank=False,
        choices=BucketTypeChoices.choices,
        default=BucketTypeChoices.IMAGE
    )

    @property
    def external_media_url(self):
        return MinioConnect().get_file_url(bucket=self.bucket, file_key=self.key)

    @property
    def cached_external_media_url(self):
        with get_redis_connection() as redis_conn:
            minio_data = redis_conn.get(f"minio-url:{self.bucket}:{self.key}")
            if not minio_data:
                minio_data = self.external_media_url
                redis_conn.set(f"minio-url:{self.bucket}:{self.key}", minio_data, ex=60*59*24*7)
            # cache almost 7 days, Minio default is 7 days
        return minio_data

    def __str__(self) -> str:
        return f"{self.key} - {self.bucket}"
