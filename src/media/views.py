from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, mixins
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from media.minio import MinioConnect
from media.models import Media
from media.serializers import UploadSerializer, MediaModelSerializer


class UploadPhotoApi(
    mixins.CreateModelMixin,
    GenericViewSet
):
    queryset = Media.objects.all()
    serializer_class = MediaModelSerializer

    def get_queryset(self):
        return self.request.user.medias.all()


@swagger_auto_schema(request_body=UploadSerializer)
class UploadApi(generics.GenericAPIView):
    """
    Custom Api for upload
        :param content_type files Content-Type
        :returns url to minio server for upload and minio url for accessing object
    """
    serializer_class = UploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            minio_client = MinioConnect()
            signed_url = minio_client.get_signed_url(serializer.data.get('bucket'))
            if signed_url:
                self.status_code = status.HTTP_200_OK
                result = {
                    'upload_url': signed_url['signed_url'],
                    'file_key': signed_url['object_name']}
                return Response(result)
            else:
                self.status_code = status.HTTP_400_BAD_REQUEST
                message = "MessageTxt.UploadFailed400"
                return Response({'message': message})
