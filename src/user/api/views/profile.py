from datetime import datetime

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import response
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    RetrieveModelMixin, DestroyModelMixin,
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.viewsets import GenericViewSet

from copytrading.models import (
    ApiKey,
    ProfileServiceApiKey
)
from copytrading.permissions import IsApiKeyOwnerPermission
from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import ServiceTypeChoices
from core.pagination import CustomPaginator, MultiplePaginationMixin
from services.models import Service, Subscription
from services.serializers.subscription import SubscriberDetailReadOnlySerializer
from user.exceptions import ChangeDefaultApiKeyImpossible
from user.models import Profile
from user.permissions import IsVendorPermission
from user.serializers import (
    ProfileModelSerializer,
    VendorProfileModelSerializer,
    ProfileCreateSerializer,
)
from user.serializers.profile import CopyApiSerializer, CopyApiEditSerializer


class ProfileViewSet(
    CreateModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    pagination_class = MultiplePaginationMixin
    ordering_field = ('-id',)

    def get_permissions(self):
        if self.action == 'vendor_subscriber':
            return IsAuthenticated(), IsVendorPermission()
        return super(ProfileViewSet, self).get_permissions()

    def get_serializer_class(self):
        if self.action == "create":
            return ProfileCreateSerializer
        if self.action == "vendor":
            return VendorProfileModelSerializer
        if self.action in ["subscribed_services", "vendor_subscriber"]:
            return SubscriberDetailReadOnlySerializer
        return ProfileModelSerializer

    def get_object(self):
        service_obj = get_object_or_404(
            Profile.objects.filter(),
            owner_id=self.request.user.owner_id
        )
        service_obj.subscribed_signal_service_count = service_obj.subscriptions.filter(
            expire_time__gte=datetime.now(),
            is_paid=True,
            service__service_type=ServiceTypeChoices.SIGNAL
        ).values('service_id').distinct().count()
        service_obj.following_number = service_obj.user_followings.all().count()
        return service_obj

    def get_queryset(self):
        if self.action == "subscribed_services":
            return Subscription.objects.filter(
                subscriber__owner_id=self.request.user.owner_id,
                expire_time__gte=datetime.now(),
                is_paid=True,
                service__service_type=ServiceTypeChoices.SIGNAL
            ).select_related('service').order_by('service_id').distinct('service_id')
        if self.action == 'vendor_subscriber':
            return Subscription.objects.filter(
                service__profile__owner_id=self.request.user.owner_id,
                service__service_type=ServiceTypeChoices.SIGNAL,
                is_paid=True,
                expire_time__gt=datetime.now()
            ).prefetch_related('subscriber').order_by('subscriber_id').distinct('subscriber_id')
        return Profile.objects.prefetch_related("services").all()

    def perform_create(self, serializer: Serializer):
        serializer.save(owner_id=self.request.user.owner_id)

    def update(self, request, *args, **kwargs):
        if 'image_id' not in request.data:
            if self.get_object().image:
                self.get_object().image.delete()
        return super(ProfileViewSet, self).update(request, *args, **kwargs)

    @action(
        methods=["PUT"],
        detail=False,
        url_path="vendor"
    )
    def vendor(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False,
    )
    def subscribed_services(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @action(
        methods=['GET'],
        detail=False,
        url_name='vendor_subscriber'
    )
    def vendor_subscriber(
            self,
            *args,
            **kwargs
    ):
        return super().list(*args, **kwargs)



class ApiKeyViewSet(
    CreateModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericViewSet
):
    queryset = ApiKey.objects.all()
    serializer_class = CopyApiSerializer

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return CopyApiEditSerializer
        return self.serializer_class

    def get_queryset(self):
        if self.action == 'list':
            return self.queryset.filter(
                owner_id=get_object_or_404(
                    Profile,
                    owner_id=self.request.user.owner_id
                ).id
            ).order_by('-is_default')
        return super(ApiKeyViewSet, self).get_queryset()

    def get_object(self):
        return get_object_or_404(
            self.queryset.filter(
                owner_id=Profile.objects.get(
                    owner_id=self.request.user.owner_id
                ).id
            ),
            pk=self.kwargs.get(
                'pk'
            )
        )

    @classmethod
    def update_is_default_logic(cls, obj, data):
        if 'is_default' in data:
            if obj.is_default and not data['is_default']:
                raise ChangeDefaultApiKeyImpossible
            elif not obj.is_default and data['is_default']:
                default_api_key = ApiKey.objects.get(owner=obj.owner, is_default=True)
                default_api_key.is_default = False
                default_api_key.save()
        else:
            data['is_default'] = obj.is_default

    def create(self, request, *args, **kwargs):
        data = request.data
        profile = Profile.objects.get(owner_id=self.request.user.owner_id)
        queryset = ApiKey.objects.filter(
            owner_id=profile.id
        )
        if queryset.exists():
            if 'is_default' in data and data['is_default']:
                queryset.update(is_default=False)
            elif 'is_default' not in data:
                data['is_default'] = False
        else:
            data['is_default'] = True
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            profile.quick_signal = True
            profile.save()
            return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if not partial:
            return Response(status=405, data={"detail": "Method 'PUT' not allowed."})
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        data = request.data
        self.update_is_default_logic(obj, data)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        profile = Profile.objects.get(owner_id=self.request.user.owner_id)
        if obj.is_default:
            queryset = ApiKey.objects.filter(
                owner_id=profile.id,
            ).exclude(id=obj.id)
            if queryset.exists():
                new_default_api_key = queryset.first()
                new_default_api_key.is_default = True
                new_default_api_key.save()
            else:
                profile.quick_signal = False
                profile.save()
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["POST"])
    def exists(
            self,
            request,
            *args,
            **kwargs
    ):
        exchange = request.data["exchange"]
        return Response(
            ApiKey.objects.filter(
                exchange=exchange.upper(),
                owner__owner_id=request.user.owner_id
            ).exists()
        )

    @action(detail=True, methods=["PUT"], permission_classes=[IsApiKeyOwnerPermission])
    def bind_to_service(
            self,
            request,
            *args,
            **kwargs
    ):
        service_id = request.data.get("service_id")
        if not service_id:
            raise APIException("service_id must be passed")

        service: Service = get_object_or_404(
            Service.objects.select_related("profile").all(),
            id=service_id
        )
        api_key: ApiKey = self.get_object()
        if service.profile.owner_id == request.user.owner_id:
            service.copy_exchange = api_key.exchange
            service.save()

        ProfileServiceApiKey.objects.get_or_create(
            service=service,
            profile=Profile.objects.get(owner_id=request.user.owner_id),
            api_key=api_key
        )
        return Response("api key binded")
