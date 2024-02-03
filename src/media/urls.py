from django.urls import path, include
from rest_framework.routers import DefaultRouter

from media.views import UploadApi, UploadPhotoApi

router = DefaultRouter()
router.register('upload', UploadPhotoApi, basename="upload-photo")

urlpatterns = [
    path('minio-url', UploadApi.as_view(), name='upload'),
    path('', include(router.urls)),
]
