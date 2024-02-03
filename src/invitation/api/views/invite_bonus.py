from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from drf_yasg.utils import swagger_auto_schema
from django.db import models
from invitation.permissions import InternalApiKeyPermission
from invitation.serializers import (InviteBonusListSerializer, FillInvitersSerializer , InviteBonusSumSerializer)
from invitation.models import InviteBonus


class InviteBonusViewSet(GenericViewSet,
                         mixins.ListModelMixin):
    # permission_classes = [InternalApiKeyPermission]

    def get_permissions(self):
        if self.action in ['list', 'fill_inviters']:
            self.permission_classes =  [InternalApiKeyPermission]
        return super(InviteBonusViewSet, self).get_permissions()

    def get_queryset(self):
        if self.action == 'list':
            return InviteBonus.objects.filter(inviter_id__isnull=True)

    def get_serializer_class(self):
        if self.action == 'list':
            return InviteBonusListSerializer
        if self.action == 'fill_inviters':
            return FillInvitersSerializer
        if self.action == 'inviter_sum':
            return InviteBonusSumSerializer
        return super().get_serializer_class()

    @swagger_auto_schema(
        responses={
            "200": InviteBonusListSerializer(many=True)
        }
    )
    def list(self, request, *args, **kwargs):
        return super(InviteBonusViewSet, self).list(request, *args, **kwargs)

    @action(methods='POST', detail=False)
    def fill_inviters(self,
                      request,
                      *args,
                      **kwargs
                      ):
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "successful"}, status=HTTP_200_OK)

    @staticmethod
    def get_invite_sum(owner_id):
        invite_sum = InviteBonus.objects.filter(inviter_id=owner_id)\
            .values('inviter_referral_code')\
            .order_by('inviter_referral_code')\
            .annotate(invite_sum=Sum('amount'))
        return invite_sum

    @action(methods='GET', detail=False)
    def inviter_sum(self,
                      request,
                      *args,
                      **kwargs
                      ):
        invite_sum = self.get_invite_sum(request.user.owner_id)
        serializer = self.get_serializer(invite_sum,many=True)
        # serializer.is_valid(raise_exception=True)
        return Response({"data": serializer.data}, status=HTTP_200_OK)
