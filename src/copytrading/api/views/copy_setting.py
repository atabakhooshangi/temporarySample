from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from user.models import Profile
from copytrading.models import CopySetting
from copytrading.serializers import CopySettingModelSerializer
from copytrading.permissions import IsCopySettingOwnerPermission


class CopySettingAPIView(GenericAPIView):
    queryset = CopySetting.objects.all()
    serializer_class = CopySettingModelSerializer
    permission_classes = [IsCopySettingOwnerPermission]

    def perform_create(self, serializer):
        return serializer.save(
            profile=Profile.objects.get(
                owner_id=self.request.user.owner_id
            )
        )

    def get_object(self):
        obj = get_object_or_404(
            self.queryset,
            profile__owner_id=self.request.user.owner_id,
            service_id=self.kwargs["pk"]
        )
        return obj

    def get(self, request, *args, **kwargs):
        user_setting = self.get_object()
        serializer = self.get_serializer(user_setting)
        return Response(
            serializer.data,
            status=HTTP_200_OK
        )

    def put(self, request, *args, **kwargs):
        user_setting = self.get_object()
        serializer = self.get_serializer(
            instance=user_setting,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        user_setting = serializer.save()
        return Response(
            self.get_serializer(user_setting).data,
            status=HTTP_200_OK
        )