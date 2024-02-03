import json
import logging
from datetime import datetime

import ccxt
from django.conf import settings
from django.db import transaction, models
from django.db.models import Q, Subquery, Case, When, Value
from django.db.models.functions import Upper
from django_filters import rest_framework as filters
from django_redis import get_redis_connection
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from copytrading.exceptions import OrderNotFoundException, OrderISNotCancel, OrderIsNotEditable
from copytrading.exchange import generate_exchange_client
from copytrading.filters import TradingOrderFilterSet, PositionFilterSet
from copytrading.models import TradingOrder, ApiKey, Position
from copytrading.serializers import ClosePositionSerializer
from copytrading.serializers.order import CopyTradingSignalCreateSerializer, CopyTradingSignalListSerializer, \
    EditTradingOrderSerializer, QuickActionPositionListSerializer, QuickActionOrderListSerializer
from copytrading.serializers.position import EditPositionSerializer
from core.base_view import MultiplePaginationViewMixin
from core.choice_field_types import (
    MessageCategoryChoices,
    ServiceStateChoices,
    StatusChoice,
    ServiceTypeChoices, PositionChoice, TradingSignalType, TradingOrderStatusChoices, TradingOrderType,
    PositionStatusChoices
)
from core.custome_mixin import CustomDestroyModelMixin
from core.pagination import MultiplePaginationMixin
from core.systemic_message import send_bulk_systemic_message
from core.utils import convertor
from invitation.permissions import InternalApiKeyPermission
from services.models import Service
from signals.exceptions import UndeletableSignal, ValueDataIsNotEditable, PositionDoesNotHaveOrder
from signals.filters import TradingSignalFilter
from signals.models import (
    TradingSignal,
    ExchangeMarket,
    UserFollowing, SignalVirtualBalance,
)
from signals.ordering import PositionOrdering, TradingOrderOrdering
from signals.permissions import IsVirtualBalanceOwner
from signals.serializers.signal import (
    TradingSignalListModelSerializer,
    ExchangeMarketReadOnlySerializer,
    TradingSignalReadOnlySerializer,
    TradingSignalWriteOnlySerializer,
    FreeTradingSignalListModelSerializer, VirtualBalanceReadOnlySerializer
)
from user.exceptions import ServiceNotFound
from user.exceptions import UserProfileNotFound
from user.models import Profile

bug_tracker_logger = logging.getLogger('bug_tracker_logger')


class SignalTradingViewSet(
    mixins.CreateModelMixin,
    CustomDestroyModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    queryset = TradingSignal.objects.all().select_related(
        "image",
        "exchange_market",
        "sid",
        "sid__profile",
        "sid__profile__image"
    )
    serializer_class = TradingSignalWriteOnlySerializer
    pagination_class = MultiplePaginationMixin
    filter_class = TradingSignalFilter
    search_fields = (
        'sid__profile__username',
        'sid__profile__title',
        'sid__title'
    )

    def get_permissions(self):
        if self.request.META.get('HTTP_X_IAM_BOT') == 'true':
            setattr(self.request.user, "owner_id", self.request.data.get("owner_id"))
            print("OWNER", self.request.user.owner_id)
            self.permission_classes = [InternalApiKeyPermission]
        return super(SignalTradingViewSet, self).get_permissions()

    def get_object(self):
        return TradingSignal.custom_objects.leaf(self.kwargs.get('pk'))

    def get_queryset(self):
        if self.action == 'follow':
            profile = get_object_or_404(
                Profile,
                owner_id=self.request.user.owner_id
            )
            following_profile_ids = UserFollowing.objects.filter(
                user=profile
            ).values_list(
                'following_id',
                flat=True
            )
            return self.queryset.filter(
                sid__profile_id__in=following_profile_ids
            )
        elif self.action == 'close':
            return self.queryset.select_related("sid__profile")
        elif self.action in ['feed', 'recommend']:
            profile = get_object_or_404(
                Profile,
                owner_id=self.request.user.owner_id
            )
            follow_profile_ids = UserFollowing.objects.filter(
                user_id=profile.id
            ).values_list(
                'following_id',
                flat=True
            )
            if self.action == 'feed':
                return self.queryset.filter(
                    Q(sid__state=ServiceStateChoices.PUBLISH) &
                    (
                            (
                                    Q(sid__subscription__subscriber__owner_id=self.request.user.owner_id) &
                                    Q(sid__subscription__is_paid=True) &
                                    Q(sid__subscription__expire_time__gte=datetime.now())
                            ) |
                            Q(sid__profile_id__in=follow_profile_ids)
                    )
                ).distinct().order_by(
                    '-created_at',
                    '-sid__subscription_fee',
                )
            if self.action == 'recommend':
                return self.queryset.filter(
                    Q(sid__state=ServiceStateChoices.PUBLISH),
                    Q(vip=False),
                    ~Q(sid__profile_id__in=follow_profile_ids),
                    ~Q(sid__profile__owner_id=self.request.user.owner_id),
                    ~Q(sid__subscription__subscriber__owner_id=self.request.user.owner_id)
                ).distinct().order_by(
                    '-created_at',
                    '-sid__subscription_fee',
                )
        return self.queryset.select_related(
            'sid',
            'exchange_market'
        )

    def get_serializer_class(self):
        if self.action in [
            'list',
            'follow',
            'feed',
            'recommend'
        ]:
            return TradingSignalListModelSerializer
        if self.action == 'retrieve':
            return TradingSignalReadOnlySerializer
        return self.serializer_class

    # TODO : ADD authentication for update and delete just if vendor is user
    def get_serializer_context(self):
        data = super().get_serializer_context()
        data['action'] = self.action
        risk_free = False
        if self.action == 'update':
            obj = self.get_object()

            if obj.state == StatusChoice.START and obj.pnl_percentage > 0:
                is_long_position = self.request.data['position'] == PositionChoice.LONG
                is_short_position = self.request.data['position'] == PositionChoice.SHORT
                is_spot = self.request.data['type'] == TradingSignalType.SPOT
                entry_point = self.request.data['entry_point']
                stop_loss = self.request.data['stop_los']
                take_profile_1 = self.request.data['take_profit_1']
                if (is_long_position and entry_point <= stop_loss < take_profile_1) or \
                        (is_short_position and entry_point >= stop_loss > take_profile_1) or \
                        (is_spot and entry_point <= stop_loss < take_profile_1):
                    risk_free = True
                # TODO : When business want stop-los compare with live price,It become active.
                # with get_redis_connection(alias="position_tracker_cache") as redis_conn:
                #     if 'exchange_market' in self.request.data:
                #         exchange_market: ExchangeMarket = get_object_or_404(
                #             ExchangeMarket.objects.all(),
                #             id=self.request.data['exchange_market']
                #         )
                #         exchange_name = exchange_market.exchange_name
                #         coin_pair = exchange_market.coin_pair
                #         market_type = exchange_market.market_type
                #         redis_exchange_data = redis_conn.get(
                #             f"exchange:{exchange_name}:coin_pair:{coin_pair}:market_type:{market_type}"
                #         )
                #         if not redis_exchange_data:  # To do: handle if price not exist
                #             raise NotFound(
                #                 "No data for this exchange market",
                #             )
                #         exchange_market_data = json.loads(redis_exchange_data)
                #         live_price = exchange_market_data.get("ticker")[-1][4]
                #         if (is_long_position and stop_loss > live_price) or (
                #                 is_short_position and stop_loss < live_price):
                #             data['state'] = StatusChoice.CLOSE

        data['risk_free'] = risk_free
        return data

    def perform_create(self, serializer):
        try:
            service = Service.objects.filter(
                profile_id=Profile.objects.get(owner_id=self.request.user.owner_id),
                service_type=ServiceTypeChoices.SIGNAL,
            ).first()
        except Service.DoesNotExist:
            raise ServiceNotFound
        except Exception as e:
            raise UserProfileNotFound

        return serializer.save(sid=service)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        signal: TradingSignal = self.get_object()
        if signal.state in [StatusChoice.DRAFT, StatusChoice.TEST, StatusChoice.PUBLISH]:
            signal.state = StatusChoice.DELETED
            signal.save()
            SignalVirtualBalance.objects.get_or_create(service=signal.sid)
            balance = SignalVirtualBalance.objects.filter(service=signal.sid).select_for_update(of=('self',)).get()
            balance.frozen -= signal.virtual_value
            balance.save()
            send_bulk_systemic_message(
                MessageCategoryChoices.SOCIAL_SIGNAL_DELETE,
                list(
                    TradingOrder.objects.prefetch_related('profile').filter(
                        signal_ref=signal
                    ).values_list("profile__owner_id", flat=True).distinct()
                ),
                dict(
                    signal_reference_id=signal.reference_id,
                    signal_owner=signal.sid.profile.title,
                    coin_pair=signal.exchange_market.coin_name
                ),
            )
            return super(SignalTradingViewSet, self).destroy(request)
        else:
            raise UndeletableSignal

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="close",
    )
    def close(self, request, *args, **kwargs):
        # FIXME: requires heavy refactoring(testing override and logging specially)
        signal: TradingSignal = self.get_object()
        if signal.state == StatusChoice.START:
            with transaction.atomic():
                with get_redis_connection(alias="position_tracker_cache") as redis_conn:
                    exchange_market: ExchangeMarket = signal.exchange_market
                    redis_exchange_data = redis_conn.get(
                        (f"exchange:{exchange_market.exchange_name}:"
                         f"coin_pair:{exchange_market.coin_pair}:"
                         f"market_type:{exchange_market.market_type}")
                    )
                    if settings.TESTING:
                        redis_exchange_data = json.dumps(
                            dict(ticker=[[10, 10, 10, 10, 10, 10]])
                        )
                    if redis_exchange_data is not None:
                        exchange_market_data = json.loads(redis_exchange_data)
                        ohlcv_list = exchange_market_data.get("ticker")
                        if isinstance(ohlcv_list, list):
                            signal.manual_closure_price = ohlcv_list[-1][4]
                    debug_message = ("Exchange market: " + str(exchange_market.__dict__))
                    debug_message += ("Signal: " + str(signal.__dict__))
                    debug_message += ("Current saved prices: " + str(exchange_market_data))
                    bug_tracker_logger.debug("Manual signal closure ----->" + debug_message)
                signal.state = StatusChoice.CLOSE
                signal.closed_datetime = datetime.now()
                signal.save()

                # Virtual Balance Calculation Start
                SignalVirtualBalance.objects.get_or_create(service=signal.sid)
                balance = SignalVirtualBalance.objects.filter(service=signal.sid).select_for_update(of=('self',)).get()
                balance.balance += signal.pnl_amount if signal.pnl_amount is not None else 0
                balance.frozen -= signal.virtual_value
                balance.save()
                # Virtual Balance Calculation End

            send_bulk_systemic_message(
                MessageCategoryChoices.SOCIAL_SIGNAL_CLOSE,
                list(
                    Profile.objects.filter(
                        Q(subscription__service=signal.sid) |
                        Q(
                            Q(follower__vendor__services=signal.sid) &
                            Q(follower__vendor__services__subscription_fee=0)
                        )
                    ).values_list("owner_id", flat=True).distinct()
                ),
                dict(
                    signal_reference_id=signal.reference_id,
                    signal_owner=signal.sid.profile.title,
                    coin_pair=signal.exchange_market.coin_name
                ),
            )
            return Response("Success")
        else:
            raise UndeletableSignal

    def perform_update(self, serializer):
        if self.action == 'partial_update':
            return super().perform_update(serializer)
        obj = self.get_object()
        obj.is_edited = True
        if 'description' in serializer.validated_data:  # TODO: move to serializer context
            description = obj.description + '=====' + serializer.validated_data['description']
        else:
            description = obj.description
        with transaction.atomic():
            edited_signal = serializer.save(
                sid=obj.sid,
                state=self.get_serializer_context().get(
                    'state') if 'state' in self.get_serializer_context() else obj.state,
                entry_point_hit_datetime=obj.entry_point_hit_datetime,
                take_profit_1_hit_datetime=obj.take_profit_1_hit_datetime,
                take_profit_2_hit_datetime=obj.take_profit_2_hit_datetime,
                stop_los_hit_datetime=obj.stop_los_hit_datetime,
                description=description,
                pnl_percentage=obj.pnl_percentage,
                pnl_amount=obj.pnl_amount,
                max_pnl_percentage=obj.max_pnl_percentage,
                min_pnl_percentage=obj.min_pnl_percentage,
            )
            obj.child = edited_signal
            obj.edited_datetime = datetime.now()
            obj.save()
            SignalVirtualBalance.objects.get_or_create(service=obj.sid)
            balance = SignalVirtualBalance.objects.filter(service=obj.sid).select_for_update(of=('self',)).get()
            balance.frozen -= edited_signal.virtual_value
            balance.save()
            edited_signal.virtual_value = obj.virtual_value
            edited_signal.save()
        edited_signal.refresh_from_db()
        return edited_signal

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        signal: TradingSignal = self.get_object()
        data = self.request.data
        exchange_market = ExchangeMarket.objects.get(
            id=data.get('exchange_market')
            if 'exchange_market' in data
            else signal.exchange_market.id
        )
        if self.action == 'update':
            if signal.entry_point_hit_datetime and \
                    convertor(
                        data['entry_point'],
                        exchange_market.quote_currency,
                        exchange_market.base_currency,
                        'int'
                    ) != signal.entry_point:
                raise ValueDataIsNotEditable  # TODO : Change the error message
            elif signal.take_profit_1_hit_datetime and \
                    convertor(
                        data['take_profit_1'],
                        exchange_market.quote_currency,
                        exchange_market.base_currency,
                        'int'
                    ) != signal.take_profit_1:
                raise ValueDataIsNotEditable

            elif signal.take_profit_2_hit_datetime and \
                    convertor(
                        data['take_profit_2'],
                        exchange_market.quote_currency,
                        exchange_market.base_currency,
                        'int') != signal.take_profit_2:
                raise ValueDataIsNotEditable
            elif signal.stop_los_hit_datetime and \
                    convertor(
                        data['stop_los'],
                        exchange_market.quote_currency,
                        exchange_market.base_currency,
                        'int') != signal.stop_los:
                raise ValueDataIsNotEditable
        subscription_user_id_list=list(
            Profile.objects.filter(
                Q(subscription__service=signal.sid) |
                Q(
                    Q(follower__vendor__services=signal.sid) &
                    Q(follower__vendor__services__subscription_fee=0)
                )
            ).values_list("owner_id", flat=True).distinct()
        )
        order_user_id_list = list(
                    TradingOrder.objects.prefetch_related('profile').filter(
                        signal_ref=signal
                    ).values_list("profile__owner_id", flat=True).distinct()
                )
        send_bulk_systemic_message(
            MessageCategoryChoices.SOCIAL_SIGNAL_UPDATE,
            list(set(subscription_user_id_list+ order_user_id_list)),
            dict(
                signal_reference_id=signal.reference_id,
                signal_owner=signal.sid.profile.title,
                symbol=signal.exchange_market.coin_name,
            ),
        )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        signal: TradingSignal = self.get_object()
        if 'description' in request.data:
            request.data['description'] = signal.description + '=====' + request.data['description']
        return super(SignalTradingViewSet, self).partial_update(request=request, *args, **kwargs)

    @action(methods=['GET'],
            detail=False,
            url_name='follow',
            url_path='follow')
    def follow(self, request, *args, **kwargs):
        # TODO: writ test
        return super(SignalTradingViewSet, self).list(request, *args, **kwargs)

    @action(methods=['GET'],
            detail=False,
            url_name='feed',
            url_path='feed')
    def feed(self, request, *args, **kwargs):
        # TODO: writ test
        return super(SignalTradingViewSet, self).list(request, *args, **kwargs)

    @action(methods=['GET'],
            detail=False,
            url_name='recommend',
            url_path='recommend')
    def recommend(self, request, *args, **kwargs):
        # TODO: writ test
        return super(SignalTradingViewSet, self).list(request, *args, **kwargs)


@swagger_auto_schema(
    manual_parameters=[
        openapi.Parameter(
            name='status',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=False,
            enum=['OPEN', 'CLOSED']
        ),
    ]
)
class SignalQuickActionViewSet(
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = TradingOrder.objects.all()
    serializer_class = CopyTradingSignalCreateSerializer


class QuickActionOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    queryset = TradingOrder.objects.filter(service_id__isnull=True)
    serializer_class = QuickActionOrderListSerializer
    pagination_class = MultiplePaginationMixin
    filter_class = TradingOrderFilterSet

    filter_backends = [
        TradingOrderOrdering,
        filters.DjangoFilterBackend,

    ]
    ordering_fields = (
        'created_at',
        'closed_at',
    )


    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            profile = Profile.objects.get(owner_id=self.request.user.owner_id, )
            queryset = self.queryset.filter(
                Q(profile_id=profile.id),
                ~Q(state=TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE
                   )
            ).prefetch_related(
                'signal_ref__exchange_market',
                'position'
            ).annotate(
                api_key_name=Subquery(
                    ApiKey.objects.filter(
                        owner=models.OuterRef('profile'),
                        exchange=Upper(models.OuterRef('exchange'))).values('name')[:1]),
            )
            return queryset
        else:
            return self.queryset

    def get_serializer_class(self):
        if self.action == 'update':
            return EditTradingOrderSerializer
        return super().get_serializer_class()

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        if order.type == TradingOrderType.SPOT:
            raise NotImplementedError
        if order.state in [
            TradingOrderStatusChoices.CANCELLED,
            TradingOrderStatusChoices.CLOSED,
            TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE,
            TradingOrderStatusChoices.FILLED]:
            raise OrderIsNotEditable
        else:
            return super().update(request, *args, **kwargs)

    @action(methods=['GET'],
            detail=True,
            url_name='cancel')
    def cancel(self, request, *args, **kwargs):
        obj = self.get_object()
        exchange = obj.exchange
        if obj.state in [TradingOrderStatusChoices.OPEN,
                         TradingOrderStatusChoices.NEW]:  # TODO: handle the partially filled order
            api_key: ApiKey = obj.api_key
            exchange_client = generate_exchange_client(
                exchange=exchange,
                credentials=dict(
                    api_key=api_key.api_key,
                    secret=api_key.secret_key,
                    password=api_key.password,
                ),
                sandbox_mode=settings.CCXT_SANDBOX_MODE
            )
            try:
                order = exchange_client.fetch_order(obj.exchange_order_id, obj.symbol)
                exchange_client.cancel_future_order(obj.exchange_order_id, obj.symbol)
                if exchange == 'bingx':
                    obj.state = TradingOrderStatusChoices.CANCELLED
                    obj.closed_time = datetime.now()
                    obj.save()
                    return super().retrieve(request, args, kwargs)
                while order.get('info')['orderStatus'] != TradingOrderStatusChoices.CANCELLED:
                    order = exchange_client.fetch_order(obj.exchange_order_id, obj.symbol)
                    statue = order.get('info')['orderStatus']
                    obj.state = statue
                    obj.save()
                return super().retrieve(request, args, kwargs)
            except ccxt.OrderNotFound:
                raise OrderNotFoundException
            except Exception as e:
                raise e
        else:
            raise OrderISNotCancel


class QuickActionPositionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    queryset = Position.objects.filter(service_id__isnull=True)
    serializer_class = QuickActionPositionListSerializer
    pagination_class = MultiplePaginationMixin
    filter_class = PositionFilterSet

    filter_backends = [
        PositionOrdering,
        filters.DjangoFilterBackend,

    ]
    ordering_fields = (
        'created_at',
        'closed_at',
    )

    def get_queryset(self):
        if self.action == 'list':
            profile = Profile.objects.get(owner_id=self.request.user.owner_id)
            queryset = self.queryset.filter(Q(profile_id=profile.id)).prefetch_related(
                models.Prefetch('trading_orders', queryset=TradingOrder.objects.select_related(
                    'signal_ref__exchange_market',
                    'api_key',
                    'signal_ref__sid'
                ).exclude(state=TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE).order_by('id'))
            )
            return queryset
        else:
            return self.queryset

    def get_serializer_class(self):
        if self.action == 'close':
            return ClosePositionSerializer
        elif self.action == 'update':
            return EditPositionSerializer
        return super().get_serializer_class()

    @action(methods=['GET'],
            detail=True,
            url_name='close')
    def close(self, request, *args, **kwargs):
        position = self.get_object()
        orders = position.trading_orders.filter(~Q(state=TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE)).order_by(
            'id')
        if len(orders) > 0:
            order = orders[0]
        if order.type == TradingOrderType.SPOT:
            raise NotImplementedError
        elif order.type == TradingOrderType.FUTURES:
            if position.status == PositionStatusChoices.OPEN:
                serializer = self.get_serializer(position, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.update(position, order.exchange, order.coin_pair, order.api_key)
        return Response("Success")

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        order = obj.trading_orders.order_by('id').first()
        if order.type == TradingOrderType.SPOT:
            raise NotImplementedError
        else:
            request.data['order'] = order
            serializer = self.get_serializer(obj, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.update(obj, request.data)
        return Response("Success")


class ExchangeMarketListView(
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = ExchangeMarket.objects.filter(is_active=True)
    serializer_class = ExchangeMarketReadOnlySerializer
    filter_fields = (
        'market_type',
        'exchange_name'
    )
    search_fields = (
        'base_currency',
        'coin_name'
    )

    def get_permissions(self):
        if self.request.META.get('HTTP_X_IAM_BOT') == 'true':
            setattr(self.request.user, "owner_id", self.request.query_params.get("owner_id"))
            self.permission_classes = [InternalApiKeyPermission]
        return super(ExchangeMarketListView, self).get_permissions()

    @action(
        methods=["GET"],
        detail=False,
        url_name='me',
        url_path='me'
    )
    def me(self, request, *args, **kwargs):
        service_coins = Service.objects.filter(
            profile__owner_id=self.request.user.owner_id). \
            values_list('coin', flat=True)

        queryset = self.filter_queryset(
            self.get_queryset().filter(
                quote_currency__in=service_coins
            ).order_by('exchange_name')
        )
        # TODO: match the coin name and exchange market create problem
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FreeSignalListView(
    mixins.ListModelMixin,
    GenericViewSet,
    MultiplePaginationViewMixin
):
    # TODO: ADD retrievel
    authentication_classes = [BasicAuthentication]
    permission_classes = (AllowAny,)
    queryset = TradingSignal.objects.filter(
        vip=False,
        sid__state=ServiceStateChoices.PUBLISH
    ).select_related(
        "image",
        "exchange_market",
        "sid",
        "sid__profile",
        "sid__profile__image"
    ).order_by('-created_at')
    filter_backends = [
        SearchFilter,
        filters.DjangoFilterBackend,
    ]
    filter_class = TradingSignalFilter
    serializer_class = FreeTradingSignalListModelSerializer
    pagination_class = MultiplePaginationMixin
    search_fields = (
        'sid__profile__username',
        'sid__profile__title',
        'sid__title'
    )


class CryptoLivePriceAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'exchange_market_id',
                openapi.IN_QUERY,
                description=("Id of an exchange market to get the live price"
                             "of its coin pair(leave this empty for a list of live prices)"),
                type=openapi.TYPE_NUMBER,
            )
        ]
    )
    def get(self, request: Request, *args, **kwargs):
        exchange_market_id = request.query_params.get("exchange_market_id")
        with get_redis_connection(alias="position_tracker_cache") as redis_conn:
            if exchange_market_id:
                exchange_market: ExchangeMarket = get_object_or_404(
                    ExchangeMarket.objects.all(),
                    id=exchange_market_id
                )
                exchange_name = exchange_market.exchange_name
                coin_pair = exchange_market.coin_pair
                market_type = exchange_market.market_type
                redis_exchange_data = redis_conn.get(
                    f"exchange:{exchange_name}:coin_pair:{coin_pair}:market_type:{market_type}"
                )
                if not redis_exchange_data:
                    raise NotFound(
                        "No data for this exchange market",
                    )
                exchange_market_data = json.loads(redis_exchange_data)
                ohlcv = exchange_market_data.get("ticker")
                if isinstance(ohlcv, list):
                    return Response(
                        dict(
                            exchange_market_id=exchange_market_id,
                            live_price=ohlcv[-1][4],
                            exchange_name=exchange_name,
                            coin_pair=coin_pair,
                            market_type=market_type,
                        ),
                        status=HTTP_200_OK
                    )
            else:
                result = []
                for exchange_market_key in redis_conn.scan_iter(
                        "exchange:*:coin_pair:*:market_type:*"
                ):
                    exchange_market_list = exchange_market_key.decode().split(":")
                    exchange_name = exchange_market_list[1]
                    coin_pair = exchange_market_list[3]
                    market_type = exchange_market_list[5]
                    exchange_market_data = json.loads(
                        redis_conn.get(exchange_market_key)
                    )
                    ohlcv = exchange_market_data.get("ticker")
                    if isinstance(ohlcv, list) and len(ohlcv) != 0:
                        result.append(
                            dict(
                                exchange_market_id=exchange_market_data.get(
                                    "exchange_market_id"
                                ),
                                exchange_name=exchange_name,
                                coin_pair=coin_pair,
                                market_type=market_type,
                                live_price=ohlcv[-1][4],
                            ),
                        )
                return Response(result, status=HTTP_200_OK)


class VirtualBalanceAPIView(
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    permission_classes = [IsVirtualBalanceOwner]
    serializer_class = VirtualBalanceReadOnlySerializer

    def get_object(self):
        obj,created = SignalVirtualBalance.objects.get_or_create(service_id=self.kwargs.get('pk'))
        return obj

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="ID of corresponding Service for virtual balance",
                type=openapi.TYPE_NUMBER,
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        self.check_object_permissions(request,self.get_object())
        return super(VirtualBalanceAPIView, self).retrieve(request, *args, **kwargs)
