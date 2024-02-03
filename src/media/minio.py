import os
import re
import uuid
from datetime import timedelta
from minio import Minio
from django.conf import settings

IMAGE_BUCKET = 'images'


class MinioConnect:

    def __init__(self):
        self.exact_url = os.environ.get("MINIO_EXACT_URL")
        self.end_point = os.environ.get("MINIO_END_POINT")
        self.access_key = os.environ.get("MINIO_ACCESS_KEY")
        self.secret_key = os.environ.get("MINIO_SECRET_KEY")
        if os.environ.get("MINIO_IS_SECURE") == "True":
            self.is_secure = True
        else:
            self.is_secure = False
        self.expire_time = timedelta(hours=5)
        self.client = Minio(
            self.end_point,
            self.access_key,
            self.secret_key,
            secure=self.is_secure
        )

    def _get_exact_url(self, url):
        return re.sub(rf"^https?:\/\/{self.end_point}", self.exact_url, url)

    def get_signed_url(self, bucket):
        # MOCK IF IN UNITTESTS
        if settings.TESTING:
            return ""
        # MOCK IF IN UNITTESTS
        bucket = bucket
        if bucket and not self.client.bucket_exists(bucket):
            try:
                self.client.make_bucket(bucket)
            except Exception as e:
                print(e)
        elif not bucket:
            return None

        try:
            object_name = str(uuid.uuid4())
            signed_url = self.client.presigned_put_object(
                bucket,
                object_name,
                self.expire_time,
            )
            return {
                'signed_url': self._get_exact_url(signed_url),
                'object_name': object_name
            }
        except Exception as e:
            print(e)

    def get_file_url(self, bucket, file_key):
        # MOCK IF IN UNITTESTS
        if settings.TESTING:
            return ""
        # MOCK IF IN UNITTESTS

        try:
            return self._get_exact_url(
                self.client.presigned_get_object(
                    bucket_name=bucket,
                    object_name=file_key
                )
            )
        except Exception as e:
            print(e)

    def remove_file(self, bucket, file_key):
        try:
            return self.client.remove_object(bucket_name=bucket, object_name=file_key)
        except Exception as e:
            print(e)
