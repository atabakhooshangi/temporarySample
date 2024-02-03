from copy import deepcopy
from datetime import timedelta
from uuid import uuid4


from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import mixins, status
from rest_framework.views import APIView

from core import settings
from invitation.models import InvitationReferral, InvitationCode, AssignorTypeChoices, AssigneeEntities
from invitation.permissions import InternalApiKeyPermission
from invitation.serializers.invitation_referral import InvitationReferralSerializer


class InvitationReferralView(APIView):
    serializer_class = InvitationReferralSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == 'POST':
            self.permission_classes = [InternalApiKeyPermission]
        return super(InvitationReferralView, self).get_permissions()

    def generate_invitation_code(self, owner_id):
        uuid = f"REF-{owner_id}-" + uuid4().hex[:6].upper()
        invitation_code = InvitationCode.objects.create(
            code_string=uuid,
            owner_id=owner_id,
            assignor_type=AssignorTypeChoices.USER_LEVEL,
            invitation_type=settings.REFERRAL_DISCOUNT_TYPE,
            description="Referral code discount",
            invitation_amount=int(settings.REFERRAL_DISCOUNT_AMOUNT),
            only_assignor=True,
            user_limit=3,
            start_date=timezone.now(),
            expire_date=timezone.now() + timedelta(days=int(settings.REFERRAL_DISCOUNT_EXPIRE_DAYS)),
        )
        _assignee = AssigneeEntities.objects.create(
            invitation=invitation_code,
            assignee_id=[0],
        )
        return invitation_code

    def get_queryset(self):
        try:
            invitation_referral = InvitationReferral.objects.get(
                owner_id=self.request.user.owner_id,
                invitation_code__assignor_type=AssignorTypeChoices.USER_LEVEL,
                invitation_code__only_assignor=True,
            )
        except InvitationReferral.DoesNotExist:
            return None
        invitation_referral_object = deepcopy(invitation_referral)
        invitation_referral.seen = True
        invitation_referral.save()
        return invitation_referral_object

    def get(self, request, *args, **kwargs):
        invitation_referral = self.get_queryset()
        if invitation_referral is None:
            return Response(
                {'invitation_code': None},
                status=status.HTTP_200_OK
            )
        return Response(
            {'invitation_code': InvitationReferralSerializer(invitation_referral).data},
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):

        serializer = InvitationReferralSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.validated_data
            # invitation_code = self.generate_invitation_code(data["owner_id"])
            if not InvitationReferral.objects.filter(owner_id=data["owner_id"]).exists():
                InvitationReferral.objects.create(
                    owner_id=data["owner_id"],
                    referral_code=data["referral_code"],
                    invitation_code=self.generate_invitation_code(data["owner_id"]),
                )
            return Response(
                status=status.HTTP_201_CREATED
            )



