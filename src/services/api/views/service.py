from datetime import datetime, timedelta
from typing import Literal

from django.db import models, transaction
from django.db.models import Q, Count, OuterRef, Window, F, Value, Subquery, ExpressionWrapper, FloatField
from django.db.models.functions import Cast, Rank, Coalesce
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters import rest_framework as filters
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404, GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import GenericViewSet

from campaign.models import Campaign
from copytrading.filters import PositionFilterSet
from copytrading.models import (
    Position,
    TradingOrder,
    ProfileServiceApiKey
)
from copytrading.serializers import ServicePositionReadOnlySerializer
from copytrading.serializers.order import OpenTradingOrderReadOnlySerializer
from copytrading.serializers.position import ServiceOpenPositionReadOnlySerializer
from core.api_gateways import ConfigServerClient
from core.base_view import MultiplePaginationViewMixin
from core.authentication import AdminJWTAuthentication
from core.choice_field_types import (
    ServiceStateChoices,
    SubscriptionPaymentTypeChoices,
    PositionStatusChoices,
    ServiceTypeChoices,
    HistoryTypeChoices,
)
from core.choice_field_types import StatusChoice
from core.pagination import CustomPaginator, CustomCursorPaginator, MultiplePaginationMixin
from core.settings import MAX_DIGIT, DECIMAL_PLACE
from core.sql_functions import (
    PostgresRound as Round,
    SubqueryCount,
    SubquerySum, PostgresExtractDate,
)
from monolithictasks import irt_price_updater, civil_registry , bybit_price_cacher
from services.exceptions import ServiceIsNotFound, CampaignNotFound
from services.filters import ServiceFilter
from services.models import (
    Service,
    Subscription,
    DailyAggregatedPnl,
    DailyROI,
    ROIHistory
)
from services.ordering import (
    ServiceOrderingFilter,
    ServiceRankingOrdering
)
from services.permissions.services import (
    UpdateServicePermission,
    RankingServicePermission,
    UserIsServiceOwnerPermission
)
from services.serializers import (
    ServiceCreateSerializer,
    ServiceReadOnlyDetailSerializer,
)
from services.serializers import ServiceSubscribeSerializer
from services.serializers.service import (
    ServiceReadOnlySerializer,
    ServiceUpdateSerializer, CopyServiceReadOnlySerializer,
    CopyServiceDetailReadOnlySerializer, ServiceRankingSerializer, ActiveCampaignSerializer,
    ServiceMouseHoverSerializer, TraderAccountStatusSerializer
)
from services.calc_utils import (
    calc_pnl,
    calc_roi,
    calc_today_aggregated_pnl,
    calc_aggregated_pnl
)
from services.tasks import pending_service_send_email
from services.utils import get_wallex_usdt_to_toman_price
from signals.filters import TradingSignalFilter
from signals.models import (
    TradingSignal,
    UserFollowing,
    ExchangeMarket
)
from signals.models import VendorFollower
from signals.serializers.signal import (
    TradingSignalListModelSerializer,
    TradingRetrieveReadOnlyModelSerializer,
    ExchangeMarketReadOnlySerializer,
)
from user.exceptions import UserProfileNotFound
from user.models import Profile


class ServiceViewList(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return super(ServiceViewList, self).get_permissions()

    queryset = Service.objects.filter(
        is_visible=True
    ).select_related(
        "profile",
    ).prefetch_related(
        "service_signals",
        "subscriptions",
        "roi_history_services",
        "roi_history_services__rois"
    ).annotate(
        # find the number of closed signals on this service
        closed_signals_count=SubqueryCount(
            TradingSignal.objects.filter(
                sid_id=models.OuterRef("id"),
                state=StatusChoice.CLOSE
            ).values('id')
        ),
        # calculate the win rate of service, using when case
        # for returning null values when there are no closed signals
        # and using subquery
        win_rate=Round(
            models.Case(
                models.When(
                    closed_signals_count=0,
                    then=models.Value(None)
                ),
                default=Cast(
                    SubqueryCount(
                        TradingSignal.objects.filter(
                            sid_id=models.OuterRef("id"),
                            state=StatusChoice.CLOSE,
                            pnl_percentage__gt=0,
                        ).values('id')
                    ) * 100 / models.F("closed_signals_count"),
                    output_field=models.FloatField()
                ),
            ),
        ),
        follower_number=models.F("profile_id__follower_num"),
        following_number=models.F("profile_id__following_num"),
        # find the total number of signals using a subquery count expression
        signal_count=SubqueryCount(
            TradingSignal.objects.filter(
                sid_id=models.OuterRef("id"),
            ).values('id')
        ),
        # find the last percentage value of service roi using
        # a subquery expression on services daily rois(sorts with number
        # to get the last record)
        cost_and_benefit=Subquery(
            DailyROI.objects.filter(roi_history__service_id=OuterRef('id'),
                                    roi_history__history_type=HistoryTypeChoices.OVERALLY).order_by(
                '-number').values_list('percentage')[:1]
        ),
    ).defer(
        "coin",
        "is_visible",
        "platform_fee",
        "state",
        "copy_exchange",
        "balance",
        "draw_down",
        "initial_draw_down",
        "image"
    )
    serializer_class = ServiceReadOnlySerializer

    filter_backends = [
        SearchFilter,
        ServiceOrderingFilter,
        filters.DjangoFilterBackend,
    ]
    ordering_fields = (
        'subscription_fee',
        'popularity',
        'win_rate',
        'closed_datetime',
        'cost_and_benefit'
    )
    search_fields = (
        'title',  # profile title and service title always same
        'profile__username',
    )
    filter_class = ServiceFilter

    # Todo: nulls_last=True doesn't work,set it.

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # read the social ranking page signals limit config from consule
        # and save it in the context of serializer for further usage
        ranking_page_signals_limit = ConfigServerClient.get_application_settings()[
            "social_ranking_page_signals_limit"
        ]  # TODO: cache value in redis
        context["ranking_page_signals_limit"] = ranking_page_signals_limit
        return context

    def get_queryset(self):
        if self.action == 'me':
            return self.queryset.filter(profile__owner_id=self.request.user.owner_id)
        elif self.action == 'follow':
            # TODO: merge queries
            try:
                profile = Profile.objects.get(owner_id=self.request.user.owner_id)
            except Profile.DoesNotExist:
                raise UserProfileNotFound
            follow_profile_ids = UserFollowing.objects.filter(user_id=profile.id).values_list('following_id', flat=True)
            return self.queryset.filter(profile_id__in=follow_profile_ids).order_by('subscription_fee')
        elif self.action == "retrieve":
            if not self.request.user.is_authenticated:
                return self.queryset
            return self.queryset.filter(id=self.kwargs.get('pk')).annotate(
                subscription_expire_time=models.Subquery(
                    Subscription.objects.filter(
                        expire_time__gte=datetime.now(),
                        subscriber__owner_id=self.request.user.owner_id,
                        service_id=models.OuterRef("id"),
                        is_paid=True,
                    ).order_by("-expire_time").values("expire_time")[:1],
                    output_field=models.DateTimeField()
                ),
            )
        elif self.action == 'profile_hover_data':
            return self.queryset.filter(id=self.kwargs.get('pk'))
        return super().get_queryset()

    def get_serializer_class(self):
        if self.action == 'subscribe':
            return ServiceSubscribeSerializer
        elif self.action in ['retrieve', 'me']:
            return ServiceReadOnlyDetailSerializer
        elif self.action == 'profile_hover_data':
            return ServiceMouseHoverSerializer
        return super().get_serializer_class()

    # @method_decorator(cache_page(60 * 30, cache='data_cache', key_prefix='traders'))
    def list(self, request, *args, **kwargs):
        if self.action == 'list':
            self.pagination_class = MultiplePaginationMixin  # CustomPaginator
            return super().list(request, *args, **kwargs)
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=True
    )
    def profile_hover_data(
            self,
            request,
            *args,
            **kwargs
    ):
        irt_price_updater.delay()
        civil_registry.delay()
        bybit_price_cacher.delay()
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False
    )
    def me(
            self,
            request,
            *args,
            **kwargs
    ):
        return super().list(request, *args, **kwargs)

    @action(
        methods=["GET"],
        detail=False
    )
    def follow(
            self,
            request,
            *args,
            **kwargs
    ):
        return super().list(self, request, *args, **kwargs)

    @action(
        methods=["PUT"],
        detail=True
    )
    def subscribe(
            self,
            request: Request,
            *args,
            **kwargs
    ):
        """
        triggers the subscription of user on this service based
        on provided payment type(trial, crypto_paid, irt_paid)
        """
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription: Subscription = serializer.save(
            profile=Profile.objects.get(owner_id=self.request.user.owner_id)
        )
        message = ""
        data = dict()
        if subscription.payment_type == SubscriptionPaymentTypeChoices.TRIAL:
            message = "trial subscription activated"
            data = dict()
        elif subscription.payment_type == SubscriptionPaymentTypeChoices.IRT_PAID:
            message = "subscription payment in progress"
            data = dict(
                ipg_payment_url=request.build_absolute_uri(
                    reverse("ipg_redirect")
                    + f"?ipg_track_id={subscription.invoices.last().ipg_track_id}"
                )
            )
        elif subscription.payment_type == SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID:
            message = "crypto payment in progress"
            data = dict(
                ipg_payment_url=request.build_absolute_uri(
                    reverse("ipg_redirect")
                    + f"?ipg_track_id={subscription.invoices.last().ipg_track_id}"
                )
            )
        elif subscription.payment_type == SubscriptionPaymentTypeChoices.CRYPTO_INTERNAL_PAID:
            message = "paid with exwino wallet"
            data = dict()

        return Response(
            dict(
                subscription_type=subscription.payment_type,
                message=message,
                data=data
            )
        )


class CopyServiceViewList(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    filter_backends = [
        SearchFilter,
        ServiceOrderingFilter,
        filters.DjangoFilterBackend,
    ]
    ordering_fields = (
        'subscription_fee',
        'popularity',
        'win_rate',
        'closed_datetime',
        'cost_and_benefit',
        'vip_count'
    )
    search_fields = (
        'title',  # profile title and service title always same
        'profile__username',
    )
    filter_class = ServiceFilter

    @staticmethod
    def get_closed_positions_count(status: PositionStatusChoices = PositionStatusChoices.CLOSED):
        return SubqueryCount(
            Position.objects.filter(
                service_id=models.OuterRef("id"),
                status=status,
            )
        )

    @staticmethod
    def get_win_rate_annotation():
        # Subquery to count winning positions
        winning_positions = SubqueryCount(
            Position.objects.filter(
                service_id=models.OuterRef("id"),
                status=PositionStatusChoices.CLOSED,
                unrealised_pnl__gt=0,
            )
        )

        # Expression to calculate win rate
        win_rate_expression = models.Case(
            models.When(
                closed_positions_count=0,
                then=models.Value(None)
                # You might want to consider what value to return here when there's division by zero
            ),
            default=ExpressionWrapper(
                winning_positions * 100 / models.F("closed_positions_count"),
                output_field=models.FloatField(),
            ),
        )

        # Annotation for win rate
        win_rate_annotation = Round(win_rate_expression)

        return win_rate_annotation

    @staticmethod
    def get_cost_and_benefit(history_type: HistoryTypeChoices = HistoryTypeChoices.OVERALLY):
        return Subquery(
            DailyROI.objects.filter(roi_history__service_id=OuterRef('id'),
                                    roi_history__history_type=history_type).order_by(
                '-number').values_list('percentage')[:1]
        )

    @staticmethod
    def get_vip_count(is_paid: bool = True):
        return SubqueryCount(
            Subscription.objects.filter(
                service_id=models.OuterRef("id"),
                expire_time__gt=datetime.now(),
                is_paid=is_paid,
            )
        )

    @staticmethod
    def get_follower_and_following_count(target: str):
        query_dict = {
            'follower': VendorFollower.objects.filter(
                vendor_id=models.OuterRef("profile_id")
            ),
            'following': UserFollowing.objects.filter(
                user_id=models.OuterRef("profile_id")
            )
        }
        return SubqueryCount(
            query_dict[target]
        )

    def get_queryset(self):
        queryset = Service.objects.filter(
            service_type=ServiceTypeChoices.COPY,
            state=ServiceStateChoices.PUBLISH,
            is_visible=True
        ).select_related(
            "profile",
            "image",
        ).prefetch_related(
            "position_services",
            "subscriptions",
        ).annotate(
            vip_count=self.get_vip_count(),
            # combining the exists expression and a subquery
            # checks to see if the current use has binded an
            # api key to this service
            api_key_binded=models.Exists(
                models.Subquery(
                    ProfileServiceApiKey.objects.filter(
                        api_key__exchange__iexact=OuterRef("copy_exchange"),
                        service_id=OuterRef("id"),
                        profile__owner_id=self.request.user.owner_id,
                    )
                )
            ),
            follower_number=self.get_follower_and_following_count('follower'),
            following_number=self.get_follower_and_following_count('following'),
            cost_and_benefit=self.get_cost_and_benefit(),
            closed_positions_count=self.get_closed_positions_count(),
            win_rate=self.get_win_rate_annotation()

        )
        if self.action == 'retrieve':
            # finds the expire time of last valid subscription
            # for this user on this service
            return queryset.annotate(subscription_expire_time=models.Subquery(
                Subscription.objects.filter(
                    expire_time__gte=datetime.now(),
                    subscriber__owner_id=self.request.user.owner_id,
                    service_id=models.OuterRef("id"),
                    is_paid=True,
                ).order_by("-expire_time").values("expire_time")[:1],
                output_field=models.DateTimeField()
            )
            )

        # TODO: move the risk calculation from serializer to here
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CopyServiceDetailReadOnlySerializer
        return CopyServiceReadOnlySerializer


class SignalServiceViewList(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return super(SignalServiceViewList, self).get_permissions()

    def get_queryset(self):
        try:
            # TODO: change when subscription is added.
            return TradingSignal.objects.filter(
                sid=self.kwargs.get('pk')
            ).select_related(
                'exchange_market',
                "sid",
                "image",
            )
        except Service.DoesNotExist:
            raise ServiceIsNotFound

    def get_object(self):
        if self.action == 'retrieve':
            signal = TradingSignal.custom_objects.leaf(pk=self.kwargs.get('signal_id'))
            return get_object_or_404(self.get_queryset(), id=signal.id)
        else:
            return super().get_object()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            context['root_creation'] = TradingSignal.custom_objects.root(pk=self.kwargs.get('signal_id')).created_at
        return context

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TradingRetrieveReadOnlyModelSerializer
        return TradingSignalListModelSerializer

    pagination_class = MultiplePaginationMixin
    filter_class = TradingSignalFilter


class PositionServiceViewList(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):

    def get_queryset(self):
        return Position.objects.filter(
            service_id=self.kwargs.get('pk'),
            trading_order__parent_order__isnull=True
        ).prefetch_related(
            "trading_orders",
        ).distinct()

    def get_object(self):
        if self.action == 'retrieve':
            return get_object_or_404(self.get_queryset(), id=self.kwargs.get('position_id'))
        else:
            return super().get_object()

    def get_serializer_class(self):
        return ServicePositionReadOnlySerializer

    pagination_class = MultiplePaginationMixin
    filter_class = PositionFilterSet


class ServiceUpdateViewSet(
    mixins.UpdateModelMixin,
    GenericViewSet
):
    queryset = Service.objects.all().select_related("profile")
    serializer_class = ServiceUpdateSerializer
    permission_classes = [UpdateServicePermission]

    def partial_update(
            self,
            request,
            *args,
            **kwargs
    ):
        service = self.get_object()
        with transaction.atomic():
            if service.state == ServiceStateChoices.REQUESTED:
                service.state = ServiceStateChoices.PENDING
                service.save()
                vendor_username = Profile.objects.get(
                    owner_id=self.request.user.owner_id
                ).username
                pending_service_send_email.apply_async(args=[vendor_username])
            elif service.state in [ServiceStateChoices.PUBLISH,
                                   ServiceStateChoices.PENDING] and 'subscription_fee' in request.data:
                request.data.pop('subscription_fee')
            return super(ServiceUpdateViewSet, self).partial_update(request=request)


class ServiceCreateViewSet(
    mixins.CreateModelMixin,
    GenericViewSet
):
    queryset = Service.objects.all()
    serializer_class = ServiceCreateSerializer

    def perform_create(self, serializer):
        profile = get_object_or_404(
            Profile.objects.all(),
            owner_id=self.request.user.owner_id
        )  # TODO: refactor to custom 404 profile not found
        return serializer.save(
            profile=profile
        )


class ExchangeListViewSet(
    mixins.ListModelMixin,
    GenericViewSet
):
    permission_classes = [AllowAny]
    serializer_class = ExchangeMarketReadOnlySerializer
    queryset = ExchangeMarket.objects.filter(is_active=True).values('exchange_name').distinct()
    search_fields = ('exchange_name',)


class ServiceRankListViewSet(
    mixins.ListModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):

    @staticmethod
    def get_roi(
            date_range,
            subquery,
            ranking_page_signals_limit
    ):
        return Service.objects.prefetch_related('service_signals').select_related('profile').filter(
            ~Q(state=ServiceStateChoices.PUBLISH)).annotate(
            total_roi=Coalesce(
                subquery,
                Value(0),
                output_field=models.DecimalField(
                    max_digits=MAX_DIGIT,
                    decimal_places=DECIMAL_PLACE
                )
            ),
            row_number=Window(
                expression=Rank(),
                order_by=F('total_roi').desc()
            ),
            signals_count_in_range=SubqueryCount(TradingSignal.objects.filter(
                sid_id=models.OuterRef("id"),
                state=StatusChoice.CLOSE,
                closed_datetime__range=date_range
            ).values('id')),
            total_signal=SubqueryCount(TradingSignal.objects.filter(
                sid_id=models.OuterRef("id"),
                state=StatusChoice.CLOSE,
            ).values('id'))
        ).filter(total_signal__gte=ranking_page_signals_limit).order_by('-total_roi')

    def get_queryset(self):
        query_params = self.request.query_params.dict()
        today = datetime.today()
        ranking_page_signals_limit = ConfigServerClient.get_application_settings()[
            "social_ranking_page_signals_limit"
        ]
        active_campaigns = Campaign.objects.filter(show=True).values('campaign_key', 'campaign_name_fa')
        if query_params.get('ordering') == '-total_roi':
            date_range = [today - timedelta(days=30), today]
            subquery = Subquery(
                ROIHistory.objects.prefetch_related('rois').filter(
                    history_type=HistoryTypeChoices.OVERALLY,
                    service_id=OuterRef('id'),
                    roi__date=today.date() - timedelta(days=1)
                ).values('roi__percentage'),
                'roi__percentage'
            )
        elif query_params.get('ordering') == 'custom':
            try:
                campaign = Campaign.objects.get(
                    campaign_key=query_params.get('campaign_key'),
                    show=True
                )
            except Campaign.DoesNotExist:
                raise CampaignNotFound
            date_range = [campaign.start_date, campaign.end_date]
            subquery = SubquerySum(
                DailyAggregatedPnl.objects.filter(
                    service_id=OuterRef('id'),
                    date__range=[
                        campaign.start_date, campaign.end_date
                    ]
                ),
                'percentage'
            )
        else:  # default is `monthly_roi`
            # NOTE: this is because we set -30th daily pnl to zero!.
            # NOTE: increase today In order to count today's signals as well
            date_range = [today - timedelta(days=30), today + timedelta(days=1)]
            subquery = Subquery(DailyROI.objects.filter(
                roi_history__history_type=HistoryTypeChoices.MONTHLY,
                roi_history__service=OuterRef('id')
            ).order_by('-number').values('percentage')[:1])
            try:
                today_pnl = Subquery(DailyAggregatedPnl.objects.filter(
                    date=today,
                    service_id=OuterRef('id'),
                ).values('percentage')[:1])
            except DailyAggregatedPnl.DoesNotExist:
                today_pnl = 0
            subquery += today_pnl
        queryset = self.get_roi(
            date_range=date_range,
            subquery=subquery,
            ranking_page_signals_limit=ranking_page_signals_limit)
        return queryset, active_campaigns

    serializer_class = ServiceRankingSerializer
    pagination_class = MultiplePaginationMixin
    permission_classes = [RankingServicePermission]

    ordering_fields = (
        'total_roi',
    )

    # @method_decorator(cache_page(60 * 30, key_prefix='ranking'))
    # @method_decorator(vary_on_headers("Authorization", ))
    def list(self, request, *args, **kwargs):
        queryset, active_campaigns = self.get_queryset()
        active_campaigns_serializer = ActiveCampaignSerializer(data=active_campaigns, many=True)
        active_campaigns_serializer.is_valid()
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(dict(items=serializer.data,
                                                    active_campaigns=active_campaigns_serializer.data))

        serializer = self.get_serializer(queryset, many=True)
        return Response(dict(items=serializer.data, active_campaigns=active_campaigns_serializer.data))


class CalculationViewset(GenericViewSet):
    """
    use the endpoints on this viewset to trigger the
    calculation tasks. list of tasks are as below:
    1- pnl calculator: calculate the pnl of closed signals
    2- calculate roi: calculate the roi and drawdown for all services
    3- aggregated pnl calculator: calculate the aggregated pnl of services
    for all dates(one task for updating today's data and another one for all dates)
    """
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = []
    # NOTE: Only for getting rid of swagger error
    serializer_class = ServiceRankingSerializer

    def _calculation_response(self):
        return Response(
            dict(
                ok=True,
                message="passed to background task for calculation"
            ),
            status=HTTP_200_OK
        )

    @action(detail=False, methods=["GET"])
    def pnl(self, request, *args, **kwargs):
        calc_pnl(request.query_params.getlist('services_id_list'))
        return self._calculation_response()

    @action(detail=False, methods=["GET"])
    def roi(self, request, *args, **kwargs):
        calc_roi(request.query_params.getlist('services_id_list'))
        return self._calculation_response()

    @action(detail=False, methods=["GET"])
    def today_aggregated_pnl(self, request, *args, **kwargs):
        calc_today_aggregated_pnl(request.query_params.getlist('services_id_list'))
        return self._calculation_response()

    @action(detail=False, methods=["GET"])
    def aggregated_pnl(self, request, *args, **kwargs):
        calc_aggregated_pnl(request.query_params.getlist('services_id_list'))
        return self._calculation_response()


class TradingOrderServiceViewList(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    permission_classes = [UserIsServiceOwnerPermission]

    def get_queryset(self):

        try:
            return TradingOrder.objects.filter(
                service_id=self.kwargs.get('pk'),
                profile__owner_id=self.request.user.owner_id
            ).select_related(
                "service"
            )
        except Service.DoesNotExist:
            raise ServiceIsNotFound

    serializer_class = OpenTradingOrderReadOnlySerializer
    pagination_class = MultiplePaginationMixin


class OpenPositionServiceViewList(
    mixins.ListModelMixin,
    GenericViewSet
):
    def get_queryset(self):
        return Position.objects.filter(
            service__id=self.kwargs.get('pk'),
            profile__owner_id=models.F('service__profile__owner_id'),
            status=PositionStatusChoices.OPEN,
            service_id__isnull=False
        )

    serializer_class = ServiceOpenPositionReadOnlySerializer


class CopyServiceAnalysisViewSet(
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    def get_serializer_class(self):
        if self.action == 'account_status':
            return TraderAccountStatusSerializer

    @staticmethod
    def get_profit_sum():
        # Subquery to sum profit of positions
        return SubquerySum(
            Position.objects.filter(
                service_id=models.OuterRef("id"),
                status=PositionStatusChoices.CLOSED,
                profile_id=models.OuterRef("profile_id"),

            ),
            'unrealised_pnl'
        )

    @staticmethod
    def get_copy_profit_sum():
        # Subquery to sum profit of copied positions
        return SubquerySum(
            Position.objects.filter(
                ~Q(profile_id=models.OuterRef("profile_id")),
                service_id=models.OuterRef("id"),
                status=PositionStatusChoices.CLOSED,

            ),
            'unrealised_pnl'
        )

    def get_queryset(self):
        query = Service.objects.filter(id=self.kwargs.get('pk'))
        if self.action == 'account_status':
            return query.select_related(
                "profile",
                "image",
            ).prefetch_related(
                "position_services",
            ).annotate(
                trade_profit_sum=self.get_profit_sum(),
                copiers_profit_sum=self.get_copy_profit_sum(),
                membership_long=PostgresExtractDate(datetime.now() - F('created_at')),
            ).values(
                'id',
                'balance',
                'trade_profit_sum',
                'copiers_profit_sum',
                'membership_long',
            )

    @action(
        methods=["GET"],
        detail=True
    )
    def account_status(
            self,
            request,
            *args,
            **kwargs
    ):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(data=serializer.data, status=HTTP_200_OK)


class USDTPriceView(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            dict(
                usdt_price=get_wallex_usdt_to_toman_price()
            ),
            status=HTTP_200_OK
        )