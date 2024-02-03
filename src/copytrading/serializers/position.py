from datetime import datetime

import ccxt
from django.conf import settings
from django.db.models import F, Q
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from copytrading.exceptions import PositionHasBeenClosed, ApiKeyNotSetException, CCXTException, FetchCCXTTextException, NoTradingHistoryFound
from copytrading.exchange import generate_exchange_client
from copytrading.models import Position, TradingOrder, ApiKey
from copytrading.tasks import close_position_copy_orders, edit_copied_orders
from core.choice_field_types import (
    PositionSideChoice,
    OrderSideChoices,
    OrderTypeChoices,
    TradingOrderStatusChoices,
    TradingOrderType, PositionStatusChoices, ServiceTypeChoices
)
from services.exceptions import ServiceIsNotFound
from services.models import Subscription, Service
from user.models import Profile
from user.serializers.profile import ProfileReadOnlySerializer


class MyCopiedOpenPositionReadOnlyBaseModelSerializer(serializers.ModelSerializer):
    # service_profile = serializers.SerializerMethodField()
    service_owner = ProfileReadOnlySerializer(source="service__profile", read_only=True)

    class Meta:
        model = Position
        fields = (
            "id",
            "created_at",
            "updated_at",
            "symbol",
            "side",
            "status",
            "take_profit",
            "stop_loss",
            "amount",
            "avg_entry_price",
            "leverage",
            "unrealised_pnl",
            "liquidation_price",
            "avg_exit_price",
            "closed_pnl",
            "service_owner"
        )
    # def get_service_profile(self,obj):


class OpenPositionReadOnlyBaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = (
            "id",
            "created_at",
            "updated_at",
            "symbol",
            "side",
            "status",
            "take_profit",
            "stop_loss",
            "amount",
            "avg_entry_price",
            "leverage",
            "unrealised_pnl",
            "liquidation_price",
            "avg_exit_price",
            "closed_pnl"
        )


class ServiceOpenPositionReadOnlySerializer(OpenPositionReadOnlyBaseModelSerializer):
    class Meta(OpenPositionReadOnlyBaseModelSerializer.Meta):
        model = Position
        fields = OpenPositionReadOnlyBaseModelSerializer.Meta.fields

    def to_representation(self, instance):
        subscribers = Subscription.objects.filter(
            service=instance.service,
            is_paid=True,
            expire_time__gte=datetime.now()
        ).values_list('subscriber__owner_id', flat=True)
        copiers_count = Position.objects.filter(
            ~Q(profile__owner_id=F('service__profile__owner_id')),
            service__id=instance.service.id,
            symbol=instance.symbol,
            status=PositionStatusChoices.OPEN,

        ).count()

        condition = {
            "owner": self.context.get('request').user.owner_id == instance.service.profile.owner_id,
            "subscriber": (self.context['request'].user.owner_id != instance.service.profile.owner_id
                           and self.context['request'].user.owner_id in subscribers),
            "observer": (self.context['request'].user.owner_id not in subscribers and
                         self.context['request'].user.owner_id != instance.service.profile.owner_id)
        }

        if condition['observer']:
            data = {
                'id': None,
                'created_at': instance.__dict__['created_at'],
                'symbol': instance.__dict__['symbol'],
                'unrealised_pnl': instance.__dict__['unrealised_pnl'],
                'amount': instance.__dict__['amount'],
                "who": "observer",
                "copiers_count": copiers_count
            }
            return data
        if condition['owner']:
            data = super().to_representation(instance)
            data['who'] = 'owner'
            data["copiers_count"] = copiers_count
            return data
        if condition['subscriber']:
            data = super().to_representation(instance)
            data['who'] = 'subscriber'
            data["copiers_count"] = copiers_count
            return data


class ClosePositionSerializer(serializers.Serializer):

    def update(
            self,
            position: Position,
            *args,
            **kwargs
    ):
        exchange = args[0]
        coin_pair = args[1]
        api_key = args[2]
        if position.side == PositionSideChoice.LONG:
            order_opposite_side = OrderSideChoices.SELL
        else:
            order_opposite_side = OrderSideChoices.BUY
        exchange_client = generate_exchange_client(
            exchange=exchange,
            credentials=dict(
                api_key=api_key.api_key,
                secret=api_key.secret_key,
                password=api_key.password,
            ),
            sandbox_mode=settings.CCXT_SANDBOX_MODE
        )
        position_data = exchange_client.get_positions(
            [position.symbol]
        )
        if position_data.get('side') is not None:
            update_data = exchange_client.generate_updated_position_data(position_data)
            coin, pair = position.symbol.split('/')
            pair = pair.split(':')[0]
            response = exchange_client.close_position(
                position=position
            )
            exchange_client.update_closed_position(
                position=position,
                update_data=update_data,
                coin=coin,
                pair=pair,
                response=response
            )

            TradingOrder.objects.create(
                profile=position.profile,
                order_id=response["id"],
                service=position.service,
                exchange=exchange,
                symbol=position.symbol,
                coin_pair=coin_pair,
                side=order_opposite_side,
                state=TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE,
                reduce_only=True,
                amount=position.amount,
                order_type=OrderTypeChoices.MARKET,  # TODO: Add LIMIT later
                type=TradingOrderType.FUTURES,  # TODO: SPOT in far future maybe!
                position=position,
            )
            if position.trading_orders.order_by("id")[0].parent_order is None and \
                    position.trading_orders.order_by('id')[
                        0].service is not None:
                close_position_copy_orders.apply_async(
                    args=[position.id]
                )
            elif position.trading_orders.order_by('id')[0].service is None:
                position.status = PositionStatusChoices.CLOSED
                position.closed_datetime = datetime.now()
                position.save()
            return position
        else:
            raise PositionHasBeenClosed


class EditPositionSerializer(serializers.Serializer):
    stop_loss = serializers.FloatField(required=False, min_value=0)
    take_profit = serializers.FloatField(required=False, min_value=0)

    def validate(self, attrs):
        if 'stop_loss' not in attrs and 'take_profit' not in attrs:
            raise serializers.ValidationError({"error": "one of the stop loss or take profit values should passed in"},
                                              400)
        return attrs

    @atomic
    def update(self, instance: Position, *args, **kwargs):
        order = self.validated_data.get('order', instance.trading_orders.order_by('id').first())
        exchange = order.exchange
        api_key = order.api_key
        self.is_valid(raise_exception=True)
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
            edit_data = dict(
                symbol=instance.symbol,
                stop_loss=self.validated_data.get('stop_loss', None),
                take_profit=self.validated_data.get('take_profit', None),
                side=instance.side,
                amount=instance.quantity,
            )
            edit_data = {k: v for k, v in edit_data.items() if v is not None}
            edit_resp = exchange_client.edit_position(**edit_data)
        except ccxt.ExchangeError as e:
            raise CCXTException(
                detail=FetchCCXTTextException().fetch_exception(message=e.args[0], symbol=instance.symbol))
        except Exception as e:
            print(type(e))

            raise e
        if 'stop_loss' in self.validated_data:
            instance.stop_loss = self.validated_data['stop_loss']
        if 'take_profit' in self.validated_data:
            instance.take_profit = self.validated_data['take_profit']
        instance.save()
        service_ids = instance.trading_orders.all().values_list('service_id')
        if not None in list(service_ids):
            edit_copied_orders.apply_async(
                args=[instance.id, edit_data]
            )
        return OpenPositionReadOnlyBaseModelSerializer(instance).data


class HistoryFetchSerializer(serializers.Serializer):
    exchange_name = serializers.CharField(default='bybit')

    def _exchange(self):
        print(self.context.get('user_id'))
        try:
            exchange = self.validated_data['exchange_name']
            api_key: ApiKey = ApiKey.objects.get(
                exchange__iexact=exchange,
                owner__owner_id=self.context.get('user_id'),
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
        return exchange_client

    def get_service(self):
        try:
            service = Service.objects.filter(profile__owner_id=self.context.get('user_id'), service_type=ServiceTypeChoices.COPY).last()

        except Exception as e:
            raise ServiceIsNotFound
        return service

    def delete_positions(self,exchange:str):
        Position.objects.prefetch_related("trading_orders").filter(profile__owner_id=self.context.get('user_id'), exchange_name__iexact=exchange).delete()
        return "Done"

    #TODO: Still bingx don't have batch order fetch. this method needs symbol and with over 300 future symbols , this is not ideal at all.
    # @atomic
    # def bingx_history(self):
    #     service = self.get_service()
    #     self.delete_positions('bingx')
    #     exchange_client = self._exchange()
    #     profile = get_object_or_404(Profile, owner_id=self.context.get('user_id'))
    #     position_history_response = exchange_client.get_closed_pnl_in_batch()

    @atomic
    def bybit_history(self):
        service = self.get_service()
        self.delete_positions('bybit')
        exchange_client = self._exchange()
        position_history_response = exchange_client.get_closed_pnl_in_batch()
        profile = get_object_or_404(Profile, owner_id=self.context.get('user_id'))
        try:
            position_history = position_history_response['result']['list']
            if not position_history:
                raise NoTradingHistoryFound
        except Exception as e:
            raise e
        positions = []
        for history in position_history:
            positions.append(Position(
                symbol=f"{history.get('symbol').strip('USDT')}/USDT:USDT",
                profile_id=profile.id,
                side=PositionSideChoice.SHORT if history.get('side') == 'Sell' else PositionSideChoice.LONG,
                amount=history.get('cumEntryValue'),
                value=history.get('cumEntryValue'),
                quantity=history.get('qty'),
                avg_entry_price=history.get('avgEntryPrice'),
                avg_exit_price=history.get('avgExitPrice'),
                closed_pnl=history.get('closedPnl'),
                leverage=history.get('leverage'),
                closed_datetime=datetime.fromtimestamp(
                    int(str(history.get('updatedTime'))[:10])),
                created_at=datetime.fromtimestamp(
                    int(str(history.get('createdTime'))[:10])),
                status=PositionStatusChoices.CLOSED,
                exchange_name='bybit',
                service_id=service.id

            ))

        Position.objects.bulk_create(positions)
        service.history_used = True
        service.save()

        return "Done"

    def create_history(self):
        history_maker = {
            "bybit": self.bybit_history,
            # "bingx":self.bingx_history
        }

        history_maker[self.validated_data['exchange_name']]()
        return
