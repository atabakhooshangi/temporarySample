import time

from django.conf import settings
from django.db.models import Prefetch, Q
from django.db.transaction import atomic, on_commit
from rest_framework import serializers

from copytrading.exceptions import ApiKeyNotSetException
from copytrading.exchange import generate_exchange_client
from copytrading.models import TradingOrder, ApiKey, Position, CopySetting
from copytrading.serializers.copy_setting import CopySettingModelSerializer
from copytrading.tasks import create_copy_orders, cancel_open_orders
from core.base_serializer import BaseModelSerializer
from core.choice_field_types import (
    OrderTypeChoices,
    StatusChoice,
    TradingSignalType,
    OrderSideChoices,
    TradingOrderStatusChoices,
    PositionStatusChoices,
)
from core.message_text import MessageText
from media.serializers import MediaModelSerializer
from services.models import Service
from signals.exceptions import (
    SignalIsCopiedOnce,
    NotSupportQuickCopySpotSignal,
    NotSupportQuickCopyThisSignal
)
from signals.exceptions import TradingSignalIsNotFound, NotSupportSupportThisPairCoinExchagne
from signals.models import TradingSignal, ExchangeMarket
from signals.serializers.signal import ExchangeMarketReadOnlySerializer
from user.models import Profile
from user.serializers import ProfileMinimalReadOnlySerializer
from user.serializers.profile import CopyApiSerializer


class BaseCopyTradingOrderCreateSerializer(BaseModelSerializer):
    class Meta:
        model = TradingOrder
        fields = (
            "id",
            "type",
            "order_type",
            "exchange",
            "coin_pair",
            "symbol",
            "leverage",
            "side",
            "amount",
            "entry_point",
            "take_profit",
            "stop_loss",
            "reduce_only"
        )


class CopyTradingCreateOrderSerializer(BaseCopyTradingOrderCreateSerializer):
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all()
    )

    class Meta(BaseCopyTradingOrderCreateSerializer.Meta):
        model = TradingOrder
        fields = BaseCopyTradingOrderCreateSerializer.Meta.fields + (
            "service",
        )
        extra_kwargs = {
            'order_type': {"default": OrderTypeChoices.LIMIT},
            'reduce_only': {"default": False},
            'take_profit': {"required": False, "allow_null": True},
            'stop_loss': {"required": False, "allow_null": True}
        }

    @atomic
    def create(self, validated_data):
        exchange = validated_data.pop("exchange")
        owner_id = self.context["request"].user.owner_id
        validated_data["profile"] = Profile.objects.get(owner_id=owner_id)
        try:
            # TODO: Change in the method of retrieving the API key ID from the front end.
            api_key: ApiKey = ApiKey.objects.get(
                exchange__iexact=exchange,
                owner__owner_id=owner_id,
            )
        except ApiKey.DoesNotExist:
            raise ApiKeyNotSetException
        exchange_client = generate_exchange_client(
            exchange=exchange,
            credentials=dict(
                api_key=api_key.api_key,
                secret=api_key.secret_key,
                password=api_key.password,
            ),
            sandbox_mode=settings.CCXT_SANDBOX_MODE
        )
        ccxt_response = exchange_client.create_future_order(
            symbol=validated_data["symbol"],
            side=validated_data["side"].lower(),
            order_type=validated_data["order_type"].lower(),
            amount=exchange_client.get_amount(
                validated_data["amount"]
            ),
            price=validated_data["entry_point"],
            take_profit=validated_data["take_profit"],
            stop_loss=validated_data["stop_loss"],
            leverage=validated_data["leverage"],
            reduce_only=validated_data["reduce_only"]
        )
        order: TradingOrder = super().create(validated_data)
        order.exchange_order_id = exchange_client.get_ccxt_response_order_id(
            ccxt_response
        )
        order.price = validated_data["entry_point"]
        order.exchange = exchange
        order.api_key = api_key
        order.save()
        on_commit(lambda: create_copy_orders.apply_async(
            args=[order.id]
        ))
        return order


class CancelOrderSerializer(serializers.Serializer):

    @atomic
    def update(self, order: TradingOrder, owner_id: int):
        exchange = order.exchange

        api_key: ApiKey = ApiKey.objects.get(
            exchange__iexact=exchange,
            owner__owner_id=owner_id,
        )
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
            subscribers_data = Profile.objects.prefetch_related(
                Prefetch("api_keys", queryset=ApiKey.objects.filter(exchange=order.exchange)),
                Prefetch("orders", queryset=TradingOrder.objects.filter(parent_order_id=order.id)),
            ).filter(

                id__in=order.service.subscriptions.values("subscriber_id"),
                # TODO: filter subscription list(Filter Acitve subscription)
            ).values(
                "id",
                "api_key__api_key",
                "api_key__secret_key",
                "api_key__password",
                "order__exchange_order_id"
            )
            status = exchange_client.cancel_future_order(
                order.exchange_order_id,
                order.symbol
            )['info']['status']
            if status != 'CANCELLED':
                raise serializers.ValidationError({"order_status": 'Order not canceled'})
        except Exception as e:
            raise e
        order.state = TradingOrderStatusChoices.CANCELLED
        order.save()
        on_commit(lambda: cancel_open_orders.apply_async(
            args=[order.id]
        ))
        return order


class PositionMinimalReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = (
            "id",
            "side",
            "status",
            "closed_pnl",
            "amount",
            "unrealised_pnl",
            "avg_entry_price",
            "avg_exit_price",
            "closed_datetime"
        )


class CopyTradingSignalCreateSerializer(BaseCopyTradingOrderCreateSerializer):
    coin_name = serializers.CharField(write_only=True)

    class Meta(BaseCopyTradingOrderCreateSerializer.Meta):
        model = TradingOrder
        fields = BaseCopyTradingOrderCreateSerializer.Meta.fields + (
            'signal_ref',
            'coin_name',
            'api_key',
            'position_id',
        )
        extra_kwargs = {
            'order_type': {'required': False},
            'exchange': {'required': False},
            'symbol': {'required': False},
        }

    def validate_take_profit(self, value):
        data = self.context['request'].data
        if 'side' in data and data['side']:
            if data['side'] == OrderSideChoices.BUY and value <= data['entry_point']:
                raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
            elif data['side'] == OrderSideChoices.SELL and value >= data['entry_point']:
                raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
        elif data['type'] == TradingSignalType.SPOT and value <= data["entry_point"]:
            raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
        return value

    def validate_stop_loss(self, value):
        data = self.context['request'].data
        if 'side' in data and data['side']:
            if data['side'] == OrderSideChoices.BUY and value >= data['entry_point']:
                raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
            elif data['side'] == OrderSideChoices.SELL and value <= data['entry_point']:
                raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
        elif data["type"] == TradingSignalType.SPOT and value >= data["entry_point"]:
            raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
        return value

    def validate_signal_ref(self, value):
        try:
            if value.state in [StatusChoice.START, StatusChoice.CLOSE, StatusChoice.DELETED] or \
                    value.closed_datetime is not None or \
                    value.edited_datetime is not None or \
                    value.child is not None:
                raise NotSupportQuickCopyThisSignal
            else:
                if TradingOrder.objects.filter(signal_ref=value,
                                               profile__owner_id=self.context['request'].user.owner_id).exists():
                    # return value  # TODO: remove this part after test
                    raise SignalIsCopiedOnce
                else:
                    return value
        except TradingSignal.DoesNotExist:
            raise TradingSignalIsNotFound

    def create(self, validated_data):
        exchange = validated_data['exchange'].lower()
        coin_name = validated_data.pop('coin_name')
        api_key = validated_data.get('api_key').id
        try:
            exchange_market = ExchangeMarket.objects.get(exchange_name=exchange,
                                                         market_type=validated_data['type'],
                                                         coin_name=coin_name)
        except ExchangeMarket.DoesNotExist:
            raise NotSupportSupportThisPairCoinExchagne
        owner_id = self.context["request"].user.owner_id
        validated_data["profile"] = Profile.objects.get(owner_id=owner_id)
        try:
            api_key: ApiKey = ApiKey.objects.get(
                id=api_key,
                # owner_id=owner_id
            )
        except ApiKey.DoesNotExist:
            raise ApiKeyNotSetException

        exchange_client = generate_exchange_client(
            exchange=exchange,
            credentials=dict(
                api_key=api_key.api_key,
                secret=api_key.secret_key,
                password=api_key.password,
            ),
            sandbox_mode=settings.CCXT_SANDBOX_MODE
        )

        if validated_data['type'] == TradingSignalType.FUTURES:
            symbol = exchange_market.futures_symbol
            start_time = time.time()
            ccxt_response = exchange_client.create_future_order(
                symbol=symbol,
                side=validated_data["side"].lower(),
                order_type=OrderTypeChoices.LIMIT,
                amount=exchange_client.get_amount(
                    validated_data["amount"]
                ),
                price=validated_data["entry_point"],
                take_profit=validated_data["take_profit"],
                stop_loss=validated_data["stop_loss"],
                leverage=validated_data["leverage"],
                reduce_only=False
            )
            order_end_time = time.time()
            print("Create order Time: ", order_end_time - start_time, flush=True)
        else:
            raise NotSupportQuickCopySpotSignal
        validated_data['symbol'] = symbol
        order: TradingOrder = super().create(validated_data)
        order.exchange_order_id = exchange_client.get_ccxt_response_order_id(
            ccxt_response
        )
        order.price = validated_data["entry_point"]
        order.exchange = exchange
        order.signal_ref = validated_data['signal_ref']
        order.save()
        return order


class CopyTradingSignalListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    side = serializers.CharField()
    # exchange_market = ExchangeMarketReadOnlySerializer(source='signal_ref.exchange_market')
    exchange_market = serializers.SerializerMethodField()
    coin_pair = serializers.CharField()
    trader_name = serializers.SerializerMethodField()
    unrealised_pnl = serializers.DecimalField(source='position.unrealised_pnl',
                                              required=False,
                                              max_digits=14,
                                              decimal_places=4,
                                              default=None)
    liquidation_price = serializers.DecimalField(source='position.liquidation_price',
                                                 required=False,
                                                 max_digits=14,
                                                 decimal_places=4,
                                                 default=None)
    closed_pnl = serializers.DecimalField(source='position.closed_pnl',
                                          required=False,
                                          max_digits=14,
                                          decimal_places=4,
                                          default=None)
    closed_pnl_percentage = serializers.DecimalField(source='position.closed_pnl_percentage',
                                                     required=False,
                                                     max_digits=14,
                                                     decimal_places=4,
                                                     default=None)
    state = serializers.SerializerMethodField()
    service_signal = serializers.SerializerMethodField()
    entry_point = serializers.SerializerMethodField()
    take_profit = serializers.SerializerMethodField()
    stop_loss = serializers.SerializerMethodField()
    avg_exit_price = serializers.SerializerMethodField(required=False,
                                                       default=None)
    order_created_at = serializers.DateTimeField(required=False,
                                                 default=None,
                                                 source='created_at')
    created_at = serializers.DateTimeField(required=False,
                                           default=None,
                                           source='position.created_at')
    updated_at = serializers.DateTimeField(required=False,
                                           default=None,
                                           source='position.updated_at')
    order_closed_at = serializers.DateTimeField(required=False,
                                                default=None,
                                                source='closed_time')
    closed_at = serializers.DateTimeField(required=False,
                                          default=None,
                                          source='position.closed_datetime')
    amount = serializers.DecimalField(decimal_places=4,
                                      max_digits=14)
    value = serializers.DecimalField(source='position.value',
                                     required=False,
                                     max_digits=14,
                                     decimal_places=4,
                                     default=None)
    quantity = serializers.DecimalField(source='position.quantity',
                                        required=False,
                                        max_digits=14,
                                        decimal_places=4,
                                        default=None)
    position_volume = serializers.DecimalField(decimal_places=4,
                                               max_digits=14)
    leverage = serializers.SerializerMethodField()
    signal_ref = serializers.SerializerMethodField()
    type = serializers.CharField()
    api_key = CopyApiSerializer()

    # api_key = serializers.IntegerField(source='api_key.id')

    class Meta:
        fields = (
            'id',
            'exchange_market',
            'side',
            'amount',
            'value',
            'quantity',
            'created_at',
            'closed_at',
            'unrealised_pnl',
            'closed_pnl',
            'closed_pnl_percentage',
            'position_volume',
            'leverage',
            'signal_ref',
            'service_signal',
            'state',
            'api_key',
            'type',
            'trader_name',
            'entry_point',
            'stop_loss',
            'take_profit',
            'avg_exit_price'
        )

    def get_state(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state in [TradingOrderStatusChoices.OPEN, TradingOrderStatusChoices.X_OPEN]:
                return TradingOrderStatusChoices.NEW
            elif obj.state == TradingOrderStatusChoices.CLOSED:
                if obj.position.status == PositionStatusChoices.OPEN:
                    return PositionStatusChoices.OPEN
                elif obj.position.status in [
                    PositionStatusChoices.CLOSED,
                    PositionStatusChoices.X_CLOSED,
                    PositionStatusChoices.CANCELED
                ]:
                    return PositionStatusChoices.CLOSED
            else:
                return obj.state
        else:
            return obj.state

    def get_entry_point(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state == TradingOrderStatusChoices.CLOSED:
                return obj.position.avg_entry_price
            else:
                return obj.entry_point
        else:
            return obj.entry_point

    def get_take_profit(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state == TradingOrderStatusChoices.CLOSED:
                return obj.position.take_profit
            else:
                return obj.take_profit
        else:
            return obj.take_profit

    def get_stop_loss(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state == TradingOrderStatusChoices.CLOSED:
                return obj.position.stop_loss
            else:
                return obj.stop_loss
        else:
            return obj.stop_loss

    def get_avg_exit_price(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state == TradingOrderStatusChoices.CLOSED:
                return obj.position.avg_exit_price
        return None

    def get_leverage(self, obj):
        if obj.signal_ref.type == TradingSignalType.FUTURES:
            if obj.state == TradingOrderStatusChoices.CLOSED:
                return obj.position.leverage
        return obj.leverage

    def get_exchange_market(self, obj):
        if obj is None or obj.signal_ref is None:
            return None
        return ExchangeMarketReadOnlySerializer(obj.signal_ref.exchange_market).data

    def get_trader_name(self, obj):
        if obj.signal_ref is None:
            return None
        return obj.signal_ref.sid.title

    def get_service_signal(self, obj):
        if obj.signal_ref is None:
            return None
        return obj.signal_ref.sid.id

    def get_signal_ref(self, obj):
        if obj.signal_ref is None:
            return None
        return obj.signal_ref.id


class QuickActionOrderListSerializer(serializers.ModelSerializer):
    api_key = CopyApiSerializer()
    service_signal = serializers.SerializerMethodField()
    # exchange_market = ExchangeMarketReadOnlySerializer(source='signal_ref.exchange_market')
    exchange_market = serializers.SerializerMethodField()
    trader_name = serializers.SerializerMethodField()

    class Meta:
        model = TradingOrder
        fields = (
            'id',
            'exchange_market',
            'leverage',
            'side',
            'type',
            'amount',
            'quantity',
            'entry_point',
            'take_profit',
            'stop_loss',
            'state',
            'created_at',
            'closed_time',
            'signal_ref',
            'trader_name',
            'api_key',
            'service_signal'
        )

    def get_exchange_market(self, obj):
        if obj is None or obj.signal_ref is None:
            return None
        return ExchangeMarketReadOnlySerializer(obj.signal_ref.exchange_market).data

    def get_service_signal(self, obj):
        if obj.signal_ref is None:
            return None
        return obj.signal_ref.sid.id

    def get_trader_name(self, obj):
        if obj.signal_ref is None:
            return None
        return obj.signal_ref.sid.title


class QuickActionPositionListSerializer(PositionMinimalReadOnlySerializer):
    exchange_market = serializers.SerializerMethodField()
    api_key = serializers.SerializerMethodField()
    signal_ref = serializers.SerializerMethodField()
    service_signal = serializers.SerializerMethodField()
    trader_name = serializers.SerializerMethodField()

    class Meta(PositionMinimalReadOnlySerializer.Meta):
        fields = PositionMinimalReadOnlySerializer.Meta.fields + (
            'exchange_market',
            'leverage',
            'exchange_name',
            'api_key',
            'closed_pnl_percentage',
            'value',
            'quantity',
            'liquidation_price',
            'take_profit',
            'stop_loss',
            'created_at',
            'signal_ref',
            'service_signal',
            'trader_name',
        )

    def get_order(self, position):
        return position.trading_orders.first()

    def get_exchange_market(self, obj):
        order = self.get_order(obj)
        if order is None or order.signal_ref is None:
            return None
        return ExchangeMarketReadOnlySerializer(order.signal_ref.exchange_market).data

    def get_api_key(self, obj):
        order = self.get_order(obj)
        if order is None:
            return None
        return CopyApiSerializer(order.api_key).data

    def get_signal_ref(self, obj):
        order = self.get_order(obj)
        if order is None or order.signal_ref is None:
            return None
        return order.signal_ref.id

    def get_service_signal(self, obj):
        order = self.get_order(obj)
        if order is None or order.signal_ref is None:
            return None
        return order.signal_ref.sid.id

    def get_trader_name(self, obj):
        order = self.get_order(obj)
        if order is None or order.signal_ref is None:
            return None
        return order.signal_ref.sid.title


class ServiceTradingOrderHistoryReadOnlySerializer(serializers.ModelSerializer):
    position = PositionMinimalReadOnlySerializer()

    class Meta:
        model = TradingOrder
        fields = (
            "id",
            "position",
            "coin_pair",
            "leverage",
            "type",
            "order_type",
            "state",
            "amount",
            "filled_amount",
            "price",
            "stop_price",
            "entry_point",
            "created_at",
        )


class UserTradingOrderHistoryReadOnlySerializer(serializers.ModelSerializer):
    position = PositionMinimalReadOnlySerializer()
    copy_trader_title = serializers.CharField(
        source="service.profile.title"
    )
    copy_trader_username = serializers.CharField(
        source="service.profile.username"
    )
    service_title = serializers.CharField(
        source="service.title"
    )
    position_income = serializers.FloatField(
        source="position.closed_pnl",
        default=None
    )
    position_avg_exit_point = serializers.FloatField(
        source="position.avg_exit_price",
        default=None
    )

    class Meta:
        model = TradingOrder
        fields = (
            "id",
            "position",
            "coin_pair",
            "leverage",
            "type",
            "order_type",
            "state",
            "user_margin",
            "price",
            "amount",
            "entry_point",
            "position_income",
            "position_avg_exit_point",
            "created_at",
            "copy_trader_title",
            "copy_trader_username",
            "service_title",
        )


class TradingOrderReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingOrder
        fields = (
            "id",
            "service",
            "type",
            "order_type",
            "exchange",
            "coin_pair",
            "symbol",
            "leverage",
            "position",
            "position_volume",
            "side",
            "amount",
            "price",
            "entry_point",
            "take_profit",
            "stop_loss",
            "created_at",
        )


class ServicePositionReadOnlySerializer(serializers.ModelSerializer):
    trading_orders = TradingOrderReadOnlySerializer(many=True)

    class Meta:
        model = Position
        fields = (
            "id",
            "side",
            "status",
            "closed_pnl",
            "leverage",
            "unrealised_pnl",
            "avg_entry_price",
            "avg_exit_price",
            "created_at",
            "closed_datetime",
            "trading_orders",
        )

    def to_representation(self, instance):
        copiers_count = Position.objects.filter(
            trading_order__parent_order_id=instance.id).count()
        data = super(ServicePositionReadOnlySerializer, self).to_representation(instance)
        data['copiers_count'] = copiers_count
        return data


class UserCopyServiceReadOnlySerializer(serializers.ModelSerializer):
    profile = ProfileMinimalReadOnlySerializer(read_only=True)
    image = MediaModelSerializer()
    today_income = serializers.FloatField()
    total_income = serializers.FloatField()
    remaining_subscription = serializers.IntegerField()
    monthly_aggregated_pnls = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id",
            "profile",
            "title",
            "image",
            "today_income",
            "total_income",
            "exchanges",
            "subscription_fee",
            "remaining_subscription",
            "monthly_aggregated_pnls",
        )

    def get_monthly_aggregated_pnls(
            self,
            obj,
    ):
        return [
            dict(
                date=aggregated_pnl.date,
                percentage=aggregated_pnl.percentage,
                amount=aggregated_pnl.amount
            ) for aggregated_pnl in obj.monthly_aggregated_pnls
        ]


class CopyServiceDashboardReadOnlySerializer(serializers.Serializer):
    today_income = serializers.FloatField(read_only=True)
    total_income = serializers.FloatField(read_only=True)
    remaining_subscription = serializers.IntegerField(read_only=True)
    current_subscription_type = serializers.CharField(read_only=True)
    setting = serializers.SerializerMethodField(read_only=True)
    setting = serializers.SerializerMethodField(read_only=True)
    start_subscription_time = serializers.DateTimeField(read_only=True)

    def get_setting(self, obj):
        try:
            setting = CopySetting.objects.get(
                profile__owner_id=self.context["request"].user.owner_id,
                service=obj
            )
            return CopySettingModelSerializer(setting).data
        except CopySetting.DoesNotExist:
            return


class UserCopyServiceHistoryReadOnlySerializer(serializers.ModelSerializer):
    profile = ProfileMinimalReadOnlySerializer(read_only=True)
    image = MediaModelSerializer()
    total_income = serializers.FloatField()
    subscription_expire_time = serializers.DateTimeField()

    class Meta:
        model = Service
        fields = (
            "profile",
            "title",
            "copy_exchange",
            "image",
            "total_income",
            "exchanges",
            "subscription_expire_time",
        )


class OpenTradingOrderReadOnlySerializer(TradingOrderReadOnlySerializer):
    class Meta(TradingOrderReadOnlySerializer.Meta):
        model = TradingOrder
        fields = TradingOrderReadOnlySerializer.Meta.fields + (
            'filled_amount',
        )


class EditTradingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradingOrder
        fields = (
            'amount',
            'entry_point',
            'price',
            'stop_loss',
            'take_profit',
            'type',

        )
        extra_kwargs = {
            'price': {'required': False}
        }

    def edit_bingx_order(self, new_order_response, old_instance: TradingOrder, exchange_client, new_order_data: dict):
        try:
            exchange_order_id = exchange_client.get_ccxt_response_order_id(
                new_order_response
            )
            del new_order_data['order_id']
            new_order_data['exchange_order_id'] = exchange_order_id
            new_order_data['service'] = old_instance.service
            new_order_data['signal_ref'] = old_instance.signal_ref
            new_order_data['profile'] = old_instance.profile
            new_order_data['coin_pair'] = old_instance.coin_pair
            new_order_data['exchange'] = old_instance.exchange
            new_order_data['api_key'] = old_instance.api_key
            new_order_data['order_type'] = old_instance.order_type
            new_order_data['side'] = old_instance.side
            new_order_data['entry_point'] = new_order_data.get('price')
            order: TradingOrder = TradingOrder.objects.create(**new_order_data)

            old_instance.state = TradingOrderStatusChoices.CANCELLED
            old_instance.save()
        except Exception as e:
            raise e

        return order

    def update(self, instance, validated_data, *args, **kwargs):
        api_key = instance.api_key
        exchange = instance.exchange
        exchange_client = generate_exchange_client(
            exchange=exchange,
            credentials=dict(
                api_key=api_key.api_key,
                secret=api_key.secret_key,
                password=api_key.password,
            ),
            sandbox_mode=settings.CCXT_SANDBOX_MODE
        )

        if self.is_valid(raise_exception=True):
            try:
                edit_data = dict(
                    order_id=instance.exchange_order_id,
                    symbol=instance.symbol,
                    side=instance.side.lower(),
                    order_type=instance.order_type.lower(),
                    amount=self.validated_data.get('amount', instance.amount),
                    leverage=instance.leverage,
                    price=self.validated_data.get('entry_point', instance.price),
                    stop_loss=self.validated_data.get('stop_loss'),
                    take_profit=self.validated_data.get('take_profit')
                )
                edit_resp = exchange_client.edit_order(**edit_data)
                if exchange == 'bingx':
                    return self.edit_bingx_order(edit_resp, instance, exchange_client, edit_data)
            except Exception as e:
                raise e
            if 'entry_point' in self.validated_data:
                instance.entry_point = self.validated_data['entry_point']
                instance.price = self.validated_data['entry_point']
            if 'amount' in self.validated_data:
                instance.amount = self.validated_data['amount']
            if 'stop_loss' in self.validated_data:
                instance.stop_loss = self.validated_data['stop_loss']
            if 'take_profit' in self.validated_data:
                instance.take_profit = self.validated_data['take_profit']
            instance.save()
            return super().update(instance, validated_data)
