from datetime import datetime

from django.db.models import Q
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from copytrading.models import TradingOrder, ApiKey
from copytrading.serializers import order
from copytrading.serializers import position
from core.base_serializer import BaseModelSerializer
from core.choice_field_types import TradingSignalType, CloseReasonTradingSignalChoices, StatusChoice, PositionChoice, \
    TradingOrderStatusChoices, PositionStatusChoices
from core.message_text import MessageText
from core.utils import convertor
from media.serializers import MediaModelSerializer
from services.models import Service
from services.serializers import ServiceMinimalReadOnlySerializer
from signals.exceptions import ValueDataIsNotEditable, NotEnoughSignalBalance
from signals.models import TradingSignal, Market, Exchange, ExchangeMarket, Comment, SignalVirtualBalance
from signals.pnl import SignalPnLCalculator


class BaseTradingSignalWriteOnlySerializer(serializers.ModelSerializer):
    entry_point = serializers.FloatField(write_only=True)
    take_profit_1 = serializers.FloatField(write_only=True)
    take_profit_2 = serializers.FloatField(write_only=True, required=False)
    stop_los = serializers.FloatField(write_only=True)

    class Meta:
        fields = (
            'entry_point',
            'take_profit_1',
            'take_profit_2',
            'stop_los',
        )

    def to_internal_value(self, data):
        values = [
            'entry_point',
            'take_profit_1',
            'take_profit_2',
            'stop_los'
        ]
        try:
            exchange_market = ExchangeMarket.objects.get(id=data.get('exchange_market'))
        except ExchangeMarket.DoesNotExist:
            exchange_market = None
        for value in values:
            if value in data:
                if data[value] is None:
                    raise serializers.ValidationError(f"{value} could not be null!")
                data[value] = convertor(
                    data[value],
                    exchange_market.quote_currency if exchange_market else None,
                    exchange_market.base_currency if exchange_market else None,
                    'int'
                )
        return super().to_internal_value(data)


class BaseTradingSignalReadOnlySerializer(serializers.Serializer):
    entry_point = serializers.SerializerMethodField(read_only=True)
    take_profit_1 = serializers.SerializerMethodField(read_only=True)
    take_profit_2 = serializers.SerializerMethodField(read_only=True)
    stop_los = serializers.SerializerMethodField(read_only=True)

    class Meta:
        fields = (
            'entry_point',
            'take_profit_1',
            'take_profit_2',
            'stop_los',
        )

    @classmethod
    def _get_exchange_market(cls, obj):
        try:
            exchange_market = obj.exchange_market
        except ExchangeMarket.DoesNotExist:
            exchange_market = None
        return exchange_market

    def get_entry_point(self, obj):
        exchange_market = self._get_exchange_market(obj)
        return convertor(
            obj.entry_point,
            exchange_market.quote_currency if exchange_market else None,
            exchange_market.base_currency if exchange_market else None,
            'decimal'
        )

    def get_take_profit_1(self, obj):
        exchange_market = self._get_exchange_market(obj)
        return convertor(
            obj.take_profit_1,
            exchange_market.quote_currency if exchange_market else None,
            exchange_market.base_currency if exchange_market else None,
            'decimal'
        )

    def get_take_profit_2(self, obj):
        exchange_market = self._get_exchange_market(obj)
        if obj.take_profit_2:
            return convertor(
                obj.take_profit_2,
                exchange_market.quote_currency if exchange_market else None,
                exchange_market.base_currency if exchange_market else None,
                'decimal'
            )
        return obj.take_profit_2

    def get_stop_los(self, obj):
        exchange_market = self._get_exchange_market(obj)
        if obj.stop_los:
            return convertor(
                obj.stop_los,
                exchange_market.quote_currency if exchange_market else None,
                exchange_market.base_currency if exchange_market else None,
                'decimal'
            )
        return obj.stop_los


class TradingSignalWriteOnlySerializer(
    BaseModelSerializer,
    BaseTradingSignalWriteOnlySerializer
):
    # TODO: separate the update and create serializer
    image_id = serializers.IntegerField(required=False, allow_null=True)
    percentage_of_fund = serializers.FloatField(min_value=0, max_value=30,required=False)

    class Meta(BaseTradingSignalWriteOnlySerializer.Meta):
        model = TradingSignal
        fields = BaseTradingSignalWriteOnlySerializer.Meta.fields + (
            'id',
            'sid',
            'state',
            'type',
            'exchange_market',
            'position',
            'leverage',
            'percentage_of_fund',
            'volume',
            'description',
            'vip',
            'image_id',
            'entry_point_hit_datetime',
            'take_profit_1_hit_datetime',
            'take_profit_2_hit_datetime',
            'stop_los_hit_datetime',
            'pnl_amount',
            'pnl_percentage',
            'virtual_value'
        )

        extra_kwargs = {
            'take_profit_1': {
                'required': True
            },
            'image': {
                'required': False
            },
            'sid': {
                'required': False
            },
            'state': {
                'required': False,
            },
            'entry_point_hit_datetime': {
                'required': False,
                'write_only': True
            },
            'take_profit_1_hit_datetime': {
                'required': False,
                'write_only': True
            },
            'take_profit_2_hit_datetime': {
                'required': False,
                'write_only': True
            },
            'stop_los_hit_datetime': {
                'required': False,
                'write_only': True
            },
            'pnl_amount': {
                'read_only': True
            },
            'pnl_percentage': {
                'read_only': True
            },
            'created_at': {
                'write_only': True,
                'required': False
            },
            'virtual_value': {
                'required': False
            }
        }

    def validate_type(self, value):
        data = self.context['request'].data
        if value == TradingSignalType.FUTURES and ('position' not in data or data['position'] is None):
            raise serializers.ValidationError('position is required field.')
        return value

    def validate_take_profit_1(self, value):
        data = self.context['request'].data
        if 'position' in data and data['position']:
            if data['position'] == PositionChoice.LONG and value <= data['entry_point']:
                raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
            elif data['position'] == PositionChoice.SHORT and value >= data['entry_point']:
                raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
        elif data['type'] == TradingSignalType.SPOT and value <= data["entry_point"]:
            raise serializers.ValidationError(MessageText.TakeProfit1ValueNotAcceptable406)
        return value

    def validate_stop_los(self, value):
        data = self.context['request'].data
        risk_free = self.context['risk_free']
        if 'position' in data and data['position']:
            if data['position'] == PositionChoice.LONG and value >= data['entry_point'] and not risk_free:
                raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
            elif data['position'] == PositionChoice.SHORT and value <= data['entry_point'] and not risk_free:
                raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
        elif data["type"] == TradingSignalType.SPOT and value >= data["entry_point"] and not risk_free:
            raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)

        return value

    def validate_leverage(self, value):
        if value < 1:
            raise serializers.ValidationError(MessageText.LeverageUnacceptable)
        data = self.context['request'].data
        if 'position' in data and data['position']:
            if float((abs(data['entry_point'] - data['stop_los']) * 100) / data['entry_point']) * value > 100:
                raise serializers.ValidationError(MessageText.StopLosValueNotAcceptable406)
        return value

    def validate_take_profit_2(self, value):
        data = self.context['request'].data
        if 'volume' not in data or data['volume'] is None:
            raise serializers.ValidationError(MessageText.VolumeIsRequired400)
        if value == data['take_profit_1']:
            raise serializers.ValidationError(MessageText.TakeProfile2ISEqualTakeProfit1400)
        if 'position' in data and data['position']:
            if data['position'] == PositionChoice.LONG and value < data['take_profit_1']:
                raise serializers.ValidationError(MessageText.TakeProfile2ISLessThanTakeProfit1400)
            elif data['position'] == PositionChoice.SHORT and value > data['take_profit_1']:
                raise serializers.ValidationError(MessageText.TakeProfile2ISBiggerThanTakeProfit1400)
        elif data["type"] == TradingSignalType.SPOT and value < data['take_profit_1']:
            raise serializers.ValidationError(MessageText.TakeProfile2ISLessThanTakeProfit1400)
        return value

    def validate(self, attrs):
        if self.context['action'] == 'create':
            if 'percentage_of_fund' not in attrs and 'virtual_value' not in attrs:
                raise serializers.ValidationError(MessageText.EitherOneOfPOForVirtualValueRequired400)
        return attrs

    @atomic
    def create(self, validated_data):
        if validated_data["sid"].subscription_fee == 0 \
                and validated_data.get("vip", False) is True:
            raise serializers.ValidationError(MessageText.ServiceIsFree400)
        SignalVirtualBalance.objects.get_or_create(service=validated_data["sid"])
        balance = SignalVirtualBalance.objects.filter(service=validated_data["sid"]).select_for_update(of=('self',)).get()
        if ('percentage_of_fund' in validated_data and 'virtual_value' in validated_data) or ('percentage_of_fund' in validated_data and 'virtual_value' not in validated_data):
            validated_data['virtual_value']=balance.available_balance * float(validated_data['percentage_of_fund']) / 100
        if 'percentage_of_fund' not in validated_data and 'virtual_value' in validated_data:
            validated_data['percentage_of_fund']= float(validated_data['virtual_value']) / balance.available_balance * 100
        if balance.available_balance < validated_data['virtual_value']:
            raise serializers.ValidationError(MessageText.NotEnoughVirtualBalance)
        obj = super().create(validated_data)
        balance.frozen += validated_data['virtual_value']
        balance.save()

        if obj.state in [StatusChoice.TEST, StatusChoice.DRAFT, StatusChoice.PUBLISH]:
            SignalPnLCalculator(obj,
                                quote_currency=obj.exchange_market.quote_currency,
                                base_currency=obj.exchange_market.base_currency, ).possible_pnl_calculator()
        return obj

    def update(self, instance: TradingSignal, validated_data):
        if self.context['action'] in ['partial_update', 'close']:
            return super().update(instance, validated_data)
        return self.create(validated_data)


class TradingSignalReadOnlySerializer(
    BaseTradingSignalReadOnlySerializer
):
    image_id = serializers.IntegerField()
    comments_number = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseTradingSignalReadOnlySerializer.Meta):
        fields = BaseTradingSignalReadOnlySerializer.Meta.fields + (
            'id',
            'reference_id',
            'sid',
            'type',
            'exchange_market',
            'position',
            'leverage',
            'percentage_of_fund',
            'entry_point_hit_datetime',
            'take_profit_1_hit_datetime',
            'take_profit_2_hit_datetime',
            'volume',
            'stop_los_hit_datetime',
            'description',
            'state',
            'manual_closure_price',
            'start_datetime',
            'closed_datetime',
            'vip',
            'pnl_percentage',
            'pnl_amount',
            'image_id',
            'comments_number'
        )
        extra_kwargs = {'take_profit_1': {'required': True},
                        'image': {'required': False},
                        'sid': {'required': False},
                        }

    def get_comments_number(self, obj):
        comments = Comment.objects.filter(
            Q(trading_signal_id=obj.id) |
            Q(parent__trading_signal_id=obj.id)
        ).values_list('id', flat=True)
        return comments.count()


class MarketReadOnlySerializer(BaseModelSerializer):
    class Meta:
        model = Market
        fields = (
            'id',
            'market_code'
        )


class ExchangeReadOnlySerializer(BaseModelSerializer):
    market = MarketReadOnlySerializer(many=True)

    class Meta:
        model = Exchange
        fields = '__all__'


class ExchangeMarketReadOnlySerializer(BaseModelSerializer):
    class Meta:
        model = ExchangeMarket
        fields = (
            'id',
            'exchange_name',
            'coin_name',
            'coin_pair',
            'futures_symbol',
            'base_currency',
            'quote_currency',
            'market_type',
            'tick_size'
        )
        extra_kwargs = {
            'coin_name': {'required': False},
            'coin_pair': {'required': False},
            'futures_symbol': {'required': False},
            'base_currency': {'required': False},
            'quote_currency': {'required': False},
            'market_type': {'required': False},
            'tick_size': {'required': False}
        }


class ExchangeMarketCoinReadOnlyModelSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source="base_currency")

    class Meta:
        fields = ("id", "base_currency")


class TradingSignalListModelSerializer(
    BaseModelSerializer,
    BaseTradingSignalReadOnlySerializer
):
    sid = ServiceMinimalReadOnlySerializer(read_only=True)
    image = MediaModelSerializer(read_only=True)
    hit = serializers.CharField(read_only=True, source='trading_signal_hit')
    comments_number = serializers.SerializerMethodField(read_only=True)
    exchange_market = ExchangeMarketReadOnlySerializer(read_only=True)

    class Meta(BaseTradingSignalReadOnlySerializer.Meta):
        model = TradingSignal
        fields = BaseTradingSignalReadOnlySerializer.Meta.fields + (
            'id',
            'reference_id',
            'sid',
            'created_at',
            'updated_at',
            'closed_datetime',
            'exchange_market',
            'position',
            'state',
            'vip',
            'leverage',
            'pnl_percentage',
            'percentage_of_fund',
            'hit',
            'entry_point_hit_datetime',
            'take_profit_1_hit_datetime',
            'take_profit_2_hit_datetime',
            'stop_los_hit_datetime',
            'pnl_percentage',
            'manual_closure_price',
            'type',
            'image',
            'comments_number',
            'volume',
            'edited',
            'virtual_value'

        )

    def to_representation(self, data):
        """
        Serialize objects to a simple textual representation.
        """
        # TODO: change the condition when add subscription

        if data.vip:
            exchange_market: ExchangeMarket = ExchangeMarket.objects.get(id=data.__dict__['exchange_market_id'])
            sid = Service.objects.get(id=data.__dict__['sid_id'])
            if not self.context['request'].user.is_authenticated and data.state != StatusChoice.CLOSE:
                data = {
                    'id': None,
                    'created_at': data.__dict__['created_at'],
                    'updated_at': data.__dict__['updated_at'],
                    "exchange_market": {
                        "id": exchange_market.id,
                        "exchange_name": exchange_market.exchange_name,
                        "coin_name": exchange_market.coin_name,
                        "base_currency": exchange_market.base_currency,
                        "quote_currency": exchange_market.quote_currency,
                        "market_type": exchange_market.market_type
                    },
                    'sid': ServiceMinimalReadOnlySerializer(sid).data,
                    'state': data.state,
                    'entry_point_hit_datetime': data.entry_point_hit_datetime,
                    'pnl_percentage': data.pnl_percentage,
                    'percentage_of_fund': data.percentage_of_fund
                    # TODO: change the serializer(less info) call with field
                }
                return data
            elif data.state != StatusChoice.CLOSE and \
                    data.sid.profile.owner_id != self.context['request'].user.owner_id and \
                    self.context['request'].user.owner_id not in \
                    data.sid.subscriptions.filter(
                        is_paid=True,
                        expire_time__gte=datetime.now()
                    ).values_list(
                        'subscriber__owner_id',
                        flat=True
                    ):
                data = {
                    'id': None,
                    'created_at': data.__dict__['created_at'],
                    'updated_at': data.__dict__['updated_at'],
                    "exchange_market": {
                        "id": exchange_market.id,
                        "exchange_name": exchange_market.exchange_name,
                        "coin_name": exchange_market.coin_name,
                        "base_currency": exchange_market.base_currency,
                        "quote_currency": exchange_market.quote_currency,
                        "market_type": exchange_market.market_type
                    },
                    'sid': ServiceMinimalReadOnlySerializer(sid).data,
                    'state': data.state,
                    'entry_point_hit_datetime': data.entry_point_hit_datetime,
                    'pnl_percentage': data.pnl_percentage,
                    'percentage_of_fund': data.percentage_of_fund
                    # TODO: change the serializer(less info) call with field
                }
                return data
        return super(TradingSignalListModelSerializer, self).to_representation(data)

    def get_comments_number(self, obj):
        # TODO: Refactor to reduce number of queries
        parrent_comments = Comment.objects.filter(trading_signal_id=obj.id).values_list('id', flat=True)
        child_comments = Comment.objects.filter(parent_id__in=parrent_comments)
        return parrent_comments.count() + child_comments.count()


class FreeTradingSignalListModelSerializer(
    BaseModelSerializer
):
    sid = ServiceMinimalReadOnlySerializer(read_only=True)
    image = MediaModelSerializer(read_only=True)
    hit = serializers.CharField(read_only=True, source='trading_signal_hit')
    comments_number = serializers.SerializerMethodField(read_only=True)
    exchange_market = ExchangeMarketReadOnlySerializer(read_only=True)

    class Meta:
        model = TradingSignal
        fields = (
            'id',
            'reference_id',
            'sid',
            'created_at',
            'updated_at',
            'closed_datetime',
            'exchange_market',
            'position',
            'state',
            'vip',
            'leverage',
            'pnl_percentage',
            'percentage_of_fund',
            'hit',
            'manual_closure_price',
            'type',
            'image',
            'comments_number',
            'volume',
            'edited',
            'virtual_value'
        )

    def get_comments_number(self, obj):
        # TODO: Refactor to reduce number of queries
        parent_comments = Comment.objects.filter(trading_signal_id=obj.id).values_list('id', flat=True)
        child_comments = Comment.objects.filter(parent_id__in=parent_comments)
        return parent_comments.count() + child_comments.count()


class TradingRetrieveReadOnlyModelSerializer(
    TradingSignalListModelSerializer
):
    image = MediaModelSerializer(read_only=True)
    sid = ServiceMinimalReadOnlySerializer(read_only=True)
    edit_history = serializers.SerializerMethodField(read_only=True)
    signal_is_copied = serializers.BooleanField(read_only=True)
    root_creation = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TradingSignal
        fields = TradingSignalListModelSerializer.Meta.fields + (
            'root_creation',
            'percentage_of_fund',
            'description',
            'edit_history',
            'signal_is_copied'

        )

    def get_root_creation(
            self,
            obj
    ):
        return self.context['root_creation']

    def get_edit_history(self, obj):
        quote_currency = obj.exchange_market.quote_currency
        base_currency = obj.exchange_market.base_currency
        return [
            {
                'date': signal.created_at,
                'entry_point': convertor(
                    signal.entry_point,
                    quote_currency,
                    base_currency,
                    'decimal'
                ),
                'take_profit_1': convertor(
                    signal.take_profit_1,
                    quote_currency,
                    base_currency,
                    'decimal'
                ),
                'take_profit_2': convertor(
                    signal.take_profit_2,
                    quote_currency,
                    base_currency,
                    'decimal'
                ) if signal.take_profit_2 is not None else None,
                'stop_los': convertor(
                    signal.stop_los,
                    quote_currency,
                    base_currency,
                    'decimal'
                ),
                'volume': signal.volume if signal.volume is not None else None,
                'percentage_of_fund': signal.percentage_of_fund if signal.percentage_of_fund is not None else None
            }
            for signal in TradingSignal.custom_objects.descendants(pk=obj.id)
        ]

    def get_signal_is_copied(self, obj):
        if TradingOrder.objects.filter(
                id=obj.id,
                profile__owner_id=self.context['request'].user.owner_id
        ).exists():
            return False
        return True


class EditCopyTradingSignalSerializer(serializers.Serializer):
    amount = serializers.FloatField(min_value=0, required=False)
    entry_point = serializers.FloatField(min_value=0, required=False)
    stop_loss = serializers.FloatField(min_value=0, required=False)
    take_profit = serializers.FloatField(min_value=0, required=False)

    def validate_amount(self, value):
        instance = TradingOrder.objects.get(id=self.context['request'].data.get('pk'))
        if instance.state == TradingOrderStatusChoices.OPEN:
            return value
        else:
            raise ValueDataIsNotEditable

    def validate_entry_point(self, value):
        instance = TradingOrder.objects.get(id=self.context['request'].data.get('pk'))
        if instance.state == TradingOrderStatusChoices.OPEN:
            return value
        else:
            raise ValueDataIsNotEditable

    def update(self, instance: TradingOrder, validated_data):
        serialize = None
        if instance.state == TradingOrderStatusChoices.OPEN:
            serialize = order.EditTradingOrderSerializer(instance, validated_data)
            return serialize.update(instance, validated_data, instance.api_key, instance.exchange)
        elif instance.state == TradingOrderStatusChoices.CLOSED and instance.position.status == PositionStatusChoices.OPEN:
            serialize = position.EditPositionSerializer(instance.position, validated_data)
            return serialize.update(instance.position, instance.api_key, instance.exchange)


class VirtualBalanceReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalVirtualBalance
        fields = ["balance",
                  "frozen"]
