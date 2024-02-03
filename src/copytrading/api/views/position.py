from django.http import Http404
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.mixins import UpdateModelMixin

from django.db.models import Subquery, OuterRef

from copytrading.permissions import IsVendorAndIsOwner
from copytrading.serializers.position import EditPositionSerializer, MyCopiedOpenPositionReadOnlyBaseModelSerializer
from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import (
    PositionStatusChoices,
    ServiceTypeChoices,
)
from core.pagination import CustomPaginator, MultiplePaginationMixin
from services.models import Service
from services.permissions import UserIsServiceOwnerPermission
from copytrading.filters import PositionFilterSet
from copytrading.models import Position, TradingOrder, ApiKey
from copytrading.serializers import (
    OpenPositionReadOnlyBaseModelSerializer,
    ServicePositionReadOnlySerializer,
    ClosePositionSerializer,
    HistoryFetchSerializer
)


class MyCopiedPositions(ListAPIView):
    serializer_class = MyCopiedOpenPositionReadOnlyBaseModelSerializer

    def get_queryset(self):
        queryset = Position.objects.filter(
            profile__owner_id=self.request.user.owner_id
        ).select_related('service__profile', 'service')
        return queryset


class PositionListViewSet(
    ListAPIView,
    MultiplePaginationViewMixin
):
    def get_queryset(self):
        queryset = Position.objects.filter(
            profile__owner_id=self.request.user.owner_id
        )
        return queryset

    filter_class = PositionFilterSet
    pagination_class = MultiplePaginationMixin
    serializer_class = OpenPositionReadOnlyBaseModelSerializer


class ServicePositionHistoryAPIView(ListAPIView, MultiplePaginationViewMixin):
    queryset = Service.objects.filter(
        profile__is_vendor=True,
        service_type=ServiceTypeChoices.COPY
    )
    serializer_class = ServicePositionReadOnlySerializer
    permission_classes = [UserIsServiceOwnerPermission]
    pagination_class = MultiplePaginationMixin

    def get_positions_queryset(self):
        return Position.objects.filter(
            # trading_order__parent_order__isnull=True,
            profile__owner_id=self.request.user.owner_id,
            service_id=self.kwargs["pk"],
            status__in=[
                PositionStatusChoices.CLOSED,
            ]
        )

    def list_positions(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_positions_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        return self.list_positions(request, *args, **kwargs)


class ClosePositionAPIView(
    UpdateModelMixin,
    GenericAPIView
):
    serializer_class = ClosePositionSerializer

    def get_queryset(self):
        queryset = Position.objects.annotate(
            exchange=Subquery(
                TradingOrder.objects.filter(
                    position_id=OuterRef("id", )
                ).values("exchange")[:1]
            ),
            coin_pair=Subquery(
                TradingOrder.objects.filter(
                    position_id=OuterRef("id")
                ).values("coin_pair")[:1]
            ),
        ).prefetch_related("trading_orders") \
            .filter(
            profile__owner_id=self.request.user.owner_id
        )

        if not queryset:
            raise Http404
        return queryset

    serializer_class = ClosePositionSerializer

    def put(self, request, *args, **kwargs):
        position = self.get_object()
        api_key: ApiKey = ApiKey.objects.get(
            exchange__iexact=position.exchange,
            owner__owner_id=request.user.owner_id,
        )
        serializer = self.get_serializer(position, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(position, position.exchange, position.coin_pair, api_key)
        return Response("Success")


class EditPositionAPIView(
    GenericAPIView,
    UpdateModelMixin
):
    serializer_class = EditPositionSerializer
    permission_classes = [IsVendorAndIsOwner]

    queryset = Position.objects.all()

    def get_object(self):
        return Position.objects.filter(id=self.kwargs['pk']).annotate(
            exchange=Subquery(
                TradingOrder.objects.filter(
                    position_id=OuterRef("id", )
                ).values("exchange")[:1]
            )).last()

    def put(self, request, *args, **kwargs):
        position = self.get_object()
        api_key: ApiKey = ApiKey.objects.get(
            exchange__iexact=position.exchange,
            owner__owner_id=request.user.owner_id,
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.update(position, position.exchange, api_key)
        return Response(data)


class CreatePnlHistoryForVendor(
    GenericAPIView
):

    serializer_class = HistoryFetchSerializer
    permission_classes = [IsVendorAndIsOwner]

    def post(self,request,*args,**kwargs):
        data = request.data
        serializer = self.serializer_class(data=data,context={"user_id":request.user.owner_id})
        serializer.is_valid(raise_exception=True)
        serializer.create_history()
        return Response({"message":"ok"})
