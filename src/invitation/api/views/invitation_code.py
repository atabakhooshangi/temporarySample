from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.message_text import MessageText
from invitation.models import InvitationCode
from invitation.models.invitation_code import AssignorTypeChoices, AssigneeEntities, InvitationTypeChoices
from invitation.serializers.invitation_code import InvitationCodeSerializer
from services.models import Service
from user.models import Profile


class IsInvitationCodeOwnerPermission:
    pass


class InvitationCodeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = InvitationCode.objects.all()
    serializer_class = InvitationCodeSerializer
    permission_classes = (IsAuthenticated,)

    #
    @action(detail=False, methods=["GET"])
    def check(
            self,
            request,
            *args,
            **kwargs
    ):
        # check invitation code effect on service or user and calculate price of service
        code_string = kwargs.get("code")
        service_id = kwargs.get("service_id")
        invitation_code = InvitationCode.objects.filter(
            code_string=code_string,
        ).prefetch_related('assignee_entities').first()

        if not invitation_code:
            return Response(
                {"error": MessageText.InvitationCodeDoesNotExist400},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            calculation_state, message, amount, _irt_amount = invitation_code.calculate_final_price(
                get_object_or_404(Service, id=service_id)
            )
            if calculation_state:
                return Response(
                    {"price": amount},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": message},
                    status=status.HTTP_400_BAD_REQUEST
                )

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            data = serializer.validated_data
            invitation_code = InvitationCode.objects.create(
                code_string=data["code_string"],
                owner_id=request.user.owner_id,
                # NOTE: there is no is_superuser in IAMUser object, need to add it
                assignor_type=AssignorTypeChoices.ADMIN_LEVEL,
                # NOTE: there is no is_superuser in IAMUser object, need to add it
                # AssignorTypeChoices.ADMIN_LEVEL if request.user.is_superuser
                # else data["assignor_type"],
                invitation_type=data["invitation_type"],
                invitation_amount=data["invitation_amount"],
                description=data["description"],
                only_assignor=False,
                # NOTE: there is no is_superuser in IAMUser object, need to add it
                # False if request.user.is_superuser
                # else data["only_assignor"],
                user_limit=data["user_limit"],
                start_date=data["start_date"],
                expire_date=data["expire_date"],
            )

            assignee_id = AssigneeEntities.objects.create(
                invitation=invitation_code,
                assignee_id=request.data.get('assignee_entities', []),
            )
            return Response(
                self.get_serializer(invitation_code).data,
                status=status.HTTP_200_OK
            )
