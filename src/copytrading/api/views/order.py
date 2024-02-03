from datetime import datetime, time, date, timedelta

from django.db import models
from django.db.models.functions import ExtractDay
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404, GenericAPIView,
)
from rest_framework.mixins import (
    CreateModelMixin, UpdateModelMixin
)
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import GenericViewSet

from copytrading.models import TradingOrder, Position
from copytrading.serializers import (
    CopyTradingCreateOrderSerializer,
    ServiceTradingOrderHistoryReadOnlySerializer,
    UserTradingOrderHistoryReadOnlySerializer,
    UserCopyServiceHistoryReadOnlySerializer,
    UserCopyServiceReadOnlySerializer,
    CopyServiceDashboardReadOnlySerializer
)
from copytrading.serializers.order import CancelOrderSerializer
from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import (
    TradingOrderStatusChoices,
    ServiceTypeChoices,
)
from core.pagination import CustomPaginator, MultiplePaginationMixin
from core.sql_functions import SubquerySum
from services.filters import ServiceFilter
from services.models import Service, Subscription, DailyAggregatedPnl
from services.permissions import UserIsServiceOwnerPermission


class ListOrderMixin:

    def list_orders(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_orders_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CopyTradingViewSet(
    CreateModelMixin,
    GenericViewSet,
):
    queryset = TradingOrder.objects.all()

    serializer_class = CopyTradingCreateOrderSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return CopyTradingCreateOrderSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=["GET"],
        url_path="dashboard/income"
    )
    def income_dashboard(self, request, *args, **kwargs):
        start_of_day = datetime.combine(datetime.today(), time.min)
        end_of_day = datetime.combine(datetime.today(), time.max)
        result = Position.objects.filter(
            trading_order__profile__owner_id=request.user.owner_id
        ).aggregate(
            today_income=models.Sum(
                "closed_pnl",
                filter=models.Q(closed_datetime__range=[start_of_day, end_of_day])
            ),
            total_income=models.Sum(
                "closed_pnl"
            )
        )
        return Response(result, status=HTTP_200_OK)


class CancelOrderAPIView(
    UpdateModelMixin,
    GenericAPIView
):
    # permission_classes = [IsAutenticated]

    def get_queryset(self):
        obj = get_object_or_404(TradingOrder, id=self.kwargs.get('pk', None))
        return obj

    serializer_class = CancelOrderSerializer

    def put(self, request, *args, **kwargs):
        order = self.get_queryset()
        serializer = self.get_serializer()
        serializer.update(order, owner_id=request.user.owner_id)
        return Response("Success")


class ServiceTradingOrderHistoryAPIView(
    ListAPIView,
    ListOrderMixin,
    MultiplePaginationViewMixin
):
    queryset = Service.objects.filter(
        profile__is_vendor=True,
        service_type=ServiceTypeChoices.COPY
    )
    serializer_class = ServiceTradingOrderHistoryReadOnlySerializer
    permission_classes = [UserIsServiceOwnerPermission]
    pagination_class = MultiplePaginationMixin

    def get_orders_queryset(self):
        return TradingOrder.objects.filter(
            parent_order__isnull=True,
            profile__owner_id=self.request.user.owner_id,
            service_id=self.kwargs["pk"],
            state__in=[
                TradingOrderStatusChoices.CLOSED,
                TradingOrderStatusChoices.CANCELLED
            ]
        )

    def get(self, request, *args, **kwargs):
        self.check_object_permissions(request, self.get_object())
        return self.list_orders(request, *args, **kwargs)


class TradingOrderHistoryViewSet(
    ListModelMixin,
    ListOrderMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    pagination_class = MultiplePaginationMixin

    def get_orders_queryset(self):
        if self.action == "list":
            return TradingOrder.objects.select_related(
                "position",
                "service",
                "service__profile",
            ).filter(
                profile__owner_id=self.request.user.owner_id,
                state__in=[
                    TradingOrderStatusChoices.CLOSED,
                    TradingOrderStatusChoices.CANCELLED
                ]
            )

    def get_serializer_class(self):
        if self.action == "list":
            return UserTradingOrderHistoryReadOnlySerializer

    def list(self, request, *args, **kwargs):
        return self.list_orders(request, *args, **kwargs)


class UserCopyServiceAPIView(
    ListAPIView,
    MultiplePaginationViewMixin
):
    pagination_class = MultiplePaginationMixin
    filter_backends = (
        filters.DjangoFilterBackend,
    )
    filter_class = ServiceFilter
    serializer_class = UserCopyServiceReadOnlySerializer

    def get_queryset(self):
        start_of_day = datetime.combine(datetime.today(), time.min)
        end_of_day = datetime.combine(datetime.today(), time.max)
        return Service.objects.select_related(
            "profile",
            "image",
        ).prefetch_related(
            models.Prefetch(
                "daily_aggregated_pnls",
                queryset=DailyAggregatedPnl.objects.filter(
                    date__range=[
                        date.today() - timedelta(days=30), date.today()
                    ]
                ).order_by("date"),
                to_attr="monthly_aggregated_pnls"
            )).filter(
            service_type=ServiceTypeChoices.COPY,
            subscription__subscriber__owner_id=self.request.user.owner_id,
            subscription__expire_time__gt=datetime.now(),
        ).annotate(
            today_income=SubquerySum(
                Position.objects.filter(
                    trading_order__service_id=models.OuterRef("id"),
                    trading_order__profile__owner_id=self.request.user.owner_id,
                    closed_datetime__range=[start_of_day, end_of_day]
                ).distinct(),
                "closed_pnl"
            ),
            total_income=SubquerySum(
                Position.objects.filter(
                    trading_order__service_id=models.OuterRef("id"),
                    trading_order__profile__owner_id=self.request.user.owner_id,
                ).distinct(),
                "closed_pnl"
            ),
            # total_pnl_percentage=SubquerySum(
            #     Position.objects.filter(
            #         trading_order__service_id=models.OuterRef("id"),
            #         trading_order__profile__owner_id=self.request.user.owner_id,
            #     ).distinct(),
            #     "closed_pnl_percentage"
            # ),  # TODO: uncomment after adding percentage
            avg_pnl_percentage=models.Avg(
                models.Subquery(
                    Position.objects.filter(
                        trading_order__service_id=models.OuterRef("id"),
                        trading_order__profile__owner_id=self.request.user.owner_id,
                    ).distinct().values("closed_pnl_percentage")
                )
            ),
            remaining_subscription=models.Subquery(
                Subscription.objects.filter(
                    service_id=models.OuterRef("id"),
                    subscriber__owner_id=self.request.user.owner_id,
                    is_paid=True,
                ).annotate(
                    remaining_subscription=ExtractDay(
                        models.F("expire_time") - datetime.now()
                    )
                ).order_by("-expire_time").values("remaining_subscription")[:1],
            ),
        ).distinct()


class UserCopyServiceDashboardAPIView(RetrieveAPIView):
    serializer_class = CopyServiceDashboardReadOnlySerializer

    def get_queryset(self):
        start_of_day = datetime.combine(datetime.today(), time.min)
        end_of_day = datetime.combine(datetime.today(), time.max)
        now = datetime.now()
        return Service.objects.annotate(
            today_income=models.Sum(
                "position_service__closed_pnl",
                filter=models.Q(
                    position_service__closed_datetime__range=[start_of_day, end_of_day]
                )
            ),
            total_income=models.Sum(
                "position_service__closed_pnl",
            ),
            start_subscription_time=models.Subquery(
                Subscription.objects.filter(
                    subscriber__owner_id=self.request.user.owner_id,
                    expire_time__gt=datetime.now(),
                    service_id=models.OuterRef('id'),
                    is_paid=True
                ).order_by('-expire_time').values('start_time')
            ),
            remaining_subscription=models.Subquery(
                Subscription.objects.filter(
                    service_id=models.OuterRef("id"),
                    subscriber__owner_id=self.request.user.owner_id,
                    is_paid=True,
                ).annotate(
                    remaining_subscription=ExtractDay(
                        models.F("expire_time") - now
                    )
                ).order_by("-expire_time").values("remaining_subscription")[:1],
            ),
            current_subscription_type=models.Subquery(
                Subscription.objects.filter(
                    service_id=models.OuterRef("id"),
                    subscriber__owner_id=self.request.user.owner_id,
                    is_paid=True,
                ).filter(
                    models.Q(
                        models.Q(start_time__lt=now) &
                        models.Q(expire_time__gt=now)
                    ),
                ).values("payment_type")[:1]
            ),
        )


class UserCopyServiceHistoryAPIView(ListAPIView, MultiplePaginationViewMixin):
    pagination_class = MultiplePaginationMixin
    filter_backends = [
        filters.DjangoFilterBackend,
    ]
    filter_class = ServiceFilter
    serializer_class = UserCopyServiceHistoryReadOnlySerializer

    def get_queryset(self):
        return Service.objects.select_related("profile").filter(
            models.Q(
                models.Q(
                    subscription__subscriber__owner_id=self.request.user.owner_id
                ) & models.Q(subscription__expire_time__lt=datetime.now())
            ),
            service_type=ServiceTypeChoices.COPY,
        ).annotate(
            total_income=SubquerySum(
                Position.objects.filter(
                    trading_order__service_id=models.OuterRef("id"),
                    trading_order__profile__owner_id=self.request.user.owner_id,
                ),
                "closed_pnl"
            ),
            subscription_expire_time=models.Subquery(
                Subscription.objects.filter(
                    service_id=models.OuterRef("id"),
                    subscriber__owner_id=self.request.user.owner_id,
                    is_paid=True,
                ).order_by("-expire_time").values("expire_time")[:1],
                output_field=models.DateTimeField(),
            )
            # subscription_start_time=models.Subquery(
            #     Subscription.objects.filter(
            #         service_id=models.OuterRef("id"),
            #         subscriber__owner_id=self.request.user.owner_id,
            #         is_paid=True,
            #     ).order_by("-expire_time").values("start_time")[:1],
            #     output_field=models.DateTimeField(),
            # )
        ).distinct()
