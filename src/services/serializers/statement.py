import json

from django_redis import get_redis_connection
from rest_framework import serializers

from core.base_serializer import BaseModelSerializer
from core.choice_field_types import StatusChoice, HistoryTypeChoices
from core.utils import convertor
from services.cache_utils import cache_roi_and_draw_down
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from user.serializers.profile import ProfileReadOnlySerializer


class TraderStatementReadOnlySerializer(BaseModelSerializer):
    service_owner = ProfileReadOnlySerializer(source="profile")
    username = ProfileReadOnlySerializer(source="profile")
    roi_data = serializers.SerializerMethodField()
    win_rate = serializers.FloatField()
    avg_pnl_percentage = serializers.FloatField()
    profit_to_loss = serializers.FloatField()
    avg_open_minutes = serializers.CharField()
    signal_count = serializers.IntegerField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = Service
        fields = (
            'username',
            'title',
            'service_owner',
            'service_type',
            'win_rate',
            'roi_data',
            'avg_pnl_percentage',
            'profit_to_loss',
            'avg_open_minutes',
            'signal_count',
            'start_date',
            'end_date',
        )

    def get_roi_data(self, obj):
        history = self.context.get('history')
        with get_redis_connection(alias="data_cache") as redis_conn:
            cached_data = redis_conn.get(f"{history}:service_id:{obj.id}")
            if cached_data:
                return json.loads(cached_data)
            return cache_roi_and_draw_down(service=obj, expire_in=60 * 60,
                                           history_type=getattr(HistoryTypeChoices, history), include_current_day=True)


class SignalStatementHistorySerializer(serializers.ModelSerializer):
    exchange_market = serializers.SerializerMethodField()
    exit_point = serializers.SerializerMethodField()
    entry_point = serializers.SerializerMethodField()
    take_profit_1 = serializers.SerializerMethodField()
    take_profit_2 = serializers.SerializerMethodField()
    stop_los = serializers.SerializerMethodField()

    class Meta:
        model = TradingSignal
        fields = [
            'type',
            'exchange_market',
            'position',
            'leverage',
            'percentage_of_fund',
            'entry_point',
            'entry_point_hit_datetime',
            'start_datetime',
            'closed_datetime',
            'exit_point',
            'pnl_percentage',
            'take_profit_1',
            'take_profit_2',
            'stop_los',
            'signal_result'
        ]

    def get_entry_point(self, obj):
        if obj.entry_point:
            return convertor(
                obj.entry_point,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return None

    def get_take_profit_1(self, obj):
        if obj.take_profit_1:
            return convertor(
                obj.take_profit_1,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return None

    def get_take_profit_2(self, obj):
        if obj.take_profit_2:
            return convertor(
                obj.take_profit_2,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return None

    def get_stop_los(self, obj):
        if obj.stop_los:
            return convertor(
                obj.stop_los,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return None

    def get_exchange_market(self, obj):
        try:
            exchange_market = obj.exchange_market
        except ExchangeMarket.DoesNotExist:
            exchange_market = None
        return exchange_market.coin_pair

    def get_exit_point(self, obj):
        if obj.state == StatusChoice.CLOSE:
            if obj.take_profit_1_hit_datetime:
                result = obj.take_profit_1
            elif obj.take_profit_2_hit_datetime:
                result = obj.take_profit_2
            elif obj.stop_los_hit_datetime:
                result = obj.stop_los
            else:
                result = obj.manual_closure_price
            return convertor(
                result,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
