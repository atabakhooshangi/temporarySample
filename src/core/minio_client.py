# import uuid
# from datetime import timedelta, datetime
#
# from django.conf import settings
# from django.core.cache import cache
# from minio import Minio
# from minio.datatypes import PostPolicy
#
# IMAGE_BUCKET = 'images'
#
#
# class MinioConnect:
#     """Base Class for minio client to connect to minio server"""
#
#     def __init__(self):
#         self.url = settings.MINIO_URL
#         self.access_key = settings.MINIO_ACCESS_KEY
#         self.secret_key = settings.MINIO_SECRET_KEY
#         self.is_secure = settings.MINIO_IS_SECURE
#         self.expire_time = timedelta(hours=7)
#         self.client = Minio(
#             self.url,
#             self.access_key,
#             self.secret_key,
#             secure=self.is_secure
#         )
#
#     def get_signed_url(self, content_type, post_policy=None):
#         """Generate put url
#         returns none if fail
#         """
#         bucket = content_type
#         if bucket and not self.client.bucket_exists(bucket):
#             try:
#                 self.client.make_bucket(bucket)
#             except Exception as e:
#                 print(e)
#
#         elif not bucket:
#             return None
#
#         try:
#             object_name = str(uuid.uuid4())
#             signed_url = self.client.presigned_put_object(
#                 bucket,
#                 object_name,
#                 self.expire_time,
#             )
#             return {'signed_url': signed_url, 'object_name': object_name}
#         except Exception as e:
#             print(e)
#
#     def get_file_url(self, bucket, file_key):
#         try:
#             cached_url = cache.get(f'{bucket} -- {file_key}')
#             if cached_url:
#                 return cached_url
#
#             object_url = self.client.presigned_get_object(bucket_name=bucket,
#                                                           object_name=file_key,
#                                                           expires=self.expire_time)
#             cache.set(f'{bucket} -- {file_key}', object_url, 6 * 60 * 60)
#             return object_url
#         except Exception as e:
#             # if happen the exception can access to object is required
#             try:
#                 object_url = self.client.presigned_get_object(bucket_name=bucket,
#                                                               object_name=file_key,
#                                                               expires=self.expire_time)
#                 return object_url
#             except Exception as e:
#                 print(e)
#
#     def remove_file(self, bucket, file_key):
#         try:
#             return self.client.remove_object(bucket_name=bucket, object_name=file_key)
#         except Exception as e:
#             print(e)
#
#     def _get_bucket_policy(self):
#         policy_read_write = {
#             "Version": "2012-10-17",
#             "Statement": [
#                 {
#                     "Action": ["s3:ListMultipartUploadParts",
#                                "s3:GetObject",
#                                "s3:AbortMultipartUpload",
#                                ],
#                     "Sid": "readObjects",
#                     "Resource": ["arn:aws:s3:::*"],
#                     "Effect": "Allow",
#                     "Principal": "*",
#                 },
#
#                 {
#                     "Sid": "Stmt1464968483619",
#                     "Effect": "Allow",
#                     "Principal": "*",
#                     "Action": "s3:PutObject",
#                     "Resource": [
#                         "arn:aws:s3:::profile/*.jpg",
#                         "arn:aws:s3:::profile/*.jpeg",
#                         "arn:aws:s3:::profile/*.png",
#                     ]
#                 },
#                 {
#                     "Sid": "Stmt1464968483619",
#                     "Effect": "Deny",
#                     "Principal": "*",
#                     "Action": "s3:PutObject",
#                     "Resource": [
#                         "arn:aws:s3:::profile/*.jpg",
#                         "arn:aws:s3:::profile/*.jpeg",
#                         "arn:aws:s3:::profile/*.png",
#                     ]
#                 }
#             ]
#         }
#         return policy_read_write
#
#     @classmethod
#     def _get_image_post_policy(cls):
#         post_policy = PostPolicy()
#         post_policy.set_content_type('image/jpeg')
#         expires_date = datetime.utcnow() + timedelta(hours=5)
#         post_policy.set_expires(expires_date)
#
#         return post_policy
