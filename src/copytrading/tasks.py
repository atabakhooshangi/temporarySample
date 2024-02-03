import decimal
import json
import logging
import subprocess

import ccxt

from celery.utils.log import get_task_logger

from django.conf import settings
from django.db.models import Prefetch, Q
from django.core.serializers.json import DjangoJSONEncoder

from core.celery import app
from core.choice_field_types import (
    ServiceTypeChoices,
    PositionSideChoice,
    OrderSideChoices,
    TradingOrderStatusChoices,
    OrderTypeChoices,
    TradingOrderType, PositionStatusChoices
)
from services.models import Service
from user.models import Profile
from copytrading.models import TradingOrder, ApiKey, CopySetting, Position

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler = logging.FileHandler("copy_trading_results.log")
file_handler.setFormatter(formatter)

copy_trading_results_logger = logging.getLogger(__name__)
copy_trading_results_logger.setLevel(logging.DEBUG)
copy_trading_results_logger.addHandler(file_handler)

celery_logger = get_task_logger(__name__)


def build_subprocess(stdin: str) -> str:
    result = subprocess.run(
        ['python', settings.BASE_DIR / 'copy_trade_orders.py'],
        input=stdin.encode(),
        stdout=subprocess.PIPE,
    )
    return result.stdout.decode("utf-8")


@app.task(name="cancel_open_orders")
def cancel_open_orders(order_id: int):
    order: TradingOrder = TradingOrder.objects.get(id=order_id)
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
        "order__exchange_order_id",
        "order__symbol"
    )
    copy_trading_results_logger.debug(subscribers_data)
    from copytrading.serializers import TradingOrderReadOnlySerializer
    data = dict(
        action="cancel_copy_orders",
        exchange=order.exchange,
        order=TradingOrderReadOnlySerializer(order).data,
        subscribers=list(subscribers_data),
        sandbox_mode=settings.CCXT_SANDBOX_MODE,
    )
    process_result = build_subprocess(
        stdin=json.dumps(
            data,
            cls=DjangoJSONEncoder
        )
    )
    print(json.loads(process_result), '=======================')
    for subscriber_result in json.loads(process_result):
        if not subscriber_result["ok"]:
            submission_error = subscriber_result["result"]["exception_detail"]
            # state = TradingOrderStatusChoices.FAILED
            # TODO: Handle exchange error for creating trading order(at this point we
            #  only saving error code as submission error)
            # something like this --> failure_reason = ExchangeFactory.bybit_exceptions[error_code]
        else:
            state = TradingOrderStatusChoices.CANCELLED
            trade_order = TradingOrder.objects.filter(exchange_order_id=subscriber_result['order_id'])
            if trade_order.exists():
                order: TradingOrder = trade_order.first()
                order.state = state
                order.save()

    return
    # subscriber_data = subscriber_result["subscriber_data"]


@app.task(name="create_copy_orders")
def create_copy_orders(
        order_id: int
):
    #TODO: correct the get the subscriber api key based on profileserviceapikey
    order: TradingOrder = TradingOrder.objects.get(id=order_id)
    subscribers_data = Profile.objects.prefetch_related(
        Prefetch("api_keys", queryset=ApiKey.objects.filter(exchange=order.exchange)),
        Prefetch("copy_settings", queryset=CopySetting.objects.filter(service=order.service))
    ).filter(
        Q(
            Q(copy_setting__is_active=True) &
            Q(copy_setting__service=order.service)&
            Q(api_key__exchange__iexact=order.exchange)
        ),
        id__in=order.service.subscriptions.values("subscriber_id"),
        # TODO: filter subscription list(Filter Acitve subscription)
    ).values(
        "id",
        "api_key__id",
        "api_key__api_key",
        "api_key__secret_key",
        "api_key__password",
        "copy_setting__margin",
        "copy_setting__take_profit_percentage",
        "copy_setting__stop_loss_percentage",
    )
    copy_trading_results_logger.debug(subscribers_data)
    from copytrading.serializers import TradingOrderReadOnlySerializer
    data = dict(
        action="create_copy_orders",
        exchange=order.exchange,
        order=TradingOrderReadOnlySerializer(order).data,
        subscribers=list(subscribers_data),
        sandbox_mode=settings.CCXT_SANDBOX_MODE,
    )
    process_result = build_subprocess(
        stdin=json.dumps(
            data,
            cls=DjangoJSONEncoder
        )
    )
    copy_orders = []
    for subscriber_result in json.loads(process_result):
        if not subscriber_result["ok"]:
            submission_error = subscriber_result["result"]["exception_detail"]
            state = TradingOrderStatusChoices.FAILED
            # TODO: Handle exchange error for creating trading order(at this point we
            #  only saving error code as submission error)
            # something like this --> failure_reason = ExchangeFactory.bybit_exceptions[error_code]
        else:
            submission_error = None
            state = order.state
        subscriber_data = subscriber_result["subscriber_data"]
        copy_trading_results_logger.debug(subscriber_data)
        copy_orders.append(
            TradingOrder(
                parent_order_id=order_id,
                exchange_order_id=subscriber_result['result']['info']['orderId'] if subscriber_result['ok'] else " ",
                service=order.service,
                profile_id=subscriber_data["id"],
                state=state,
                type=order.type,
                position=order.position,
                exchange=order.exchange,
                symbol=order.symbol,
                coin_pair=order.coin_pair,
                leverage=order.leverage,
                order_type=order.order_type,
                side=order.side,
                amount=subscriber_data['copy_setting__margin'],
                price=order.price,
                entry_point=order.entry_point,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                user_margin=subscriber_data["copy_setting__margin"],
                user_take_profit_percentage=subscriber_data['copy_setting__take_profit_percentage'],
                user_stop_loss_percentage=subscriber_data["copy_setting__stop_loss_percentage"],
                submission_error=submission_error,
                api_key_id=subscriber_data['api_key__id']
            )
        )
    TradingOrder.objects.bulk_create(copy_orders)


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)


@app.task(name='edit_copied_orders')
def edit_copied_orders(
        position_id: int,
        edit_data: dict
):
    position = Position.objects.prefetch_related(
        "trading_orders"
    ).get(id=position_id)
    position_order: TradingOrder = position.trading_orders.all()[0]
    parent_order_id = position_order.id
    exchange = position_order.exchange
    subscribers_data = Profile.objects.prefetch_related(
        Prefetch("api_keys", queryset=ApiKey.objects.filter(exchange=exchange)),
        Prefetch("copy_settings", queryset=CopySetting.objects.filter(service=position.service)),
        Prefetch(
            "position",
            queryset=Position.objects.filter(
                service=position.service,
                trading_order__parent_order_id=parent_order_id
            ),
        )
    ).filter(
        Q(
            Q(copy_setting__is_active=True) &
            Q(copy_setting__service=position.service) &
            Q(api_key__exchange__iexact=exchange)
        ),
        id__in=position.service.subscriptions.values("subscriber_id"),  # TODO: Exclude expired subscriptions
    ).distinct().values(
        "id",
        "api_key__api_key",
        "api_key__secret_key",
        "api_key__password",
        "copy_setting__margin",
        "copy_setting__take_profit_percentage",
        "copy_setting__stop_loss_percentage",
        "position__side",
        "position__leverage",
        "position__amount",
        "position__quantity",
        "position__symbol",
        "position__id",
    )
    data = dict(
        exchange=exchange,
        action="edit_subscribers_positions",
        subscribers=list(subscribers_data),
        sandbox_mode=settings.CCXT_SANDBOX_MODE,
        edit_params=edit_data
    )
    process_result = build_subprocess(stdin=json.dumps(data, default=decimal_default))
    copy_trading_results_logger.debug(process_result)
    celery_logger.debug(process_result)
    del edit_data['symbol']
    for sub in list(subscribers_data):
        if sub['position__id']:
            to_edit_position: Position = Position.objects.get(id=sub.get('position__id'))
            for k, v in edit_data.items():
                setattr(to_edit_position, k, v)
            to_edit_position.save()
    return


@app.task(name="close_position_copy_orders")
def close_position_copy_orders(
        position_id: int

):
    position = Position.objects.prefetch_related(
        "trading_orders"
    ).get(id=position_id)
    position_order: TradingOrder = position.trading_orders.all()[0]
    parent_order_id = position_order.id
    exchange = position_order.exchange
    coin_pair = position_order.coin_pair
    subscribers_data = Profile.objects.prefetch_related(
        Prefetch("api_keys", queryset=ApiKey.objects.filter(exchange=exchange)),
        Prefetch("copy_settings", queryset=CopySetting.objects.filter(service=position.service)),
        Prefetch(
            "position",
            queryset=Position.objects.filter(
                service=position.service,
                trading_order__parent_order_id=parent_order_id
            ),
        )
    ).filter(
        Q(
            Q(copy_setting__is_active=True) &
            Q(copy_setting__service=position.service) &
            Q(api_key__exchange__iexact=exchange)
        ),
        id__in=position.service.subscriptions.values("subscriber_id"),  # TODO: Exclude expired subscriptions
    ).distinct().values(
        "id",
        "api_key__api_key",
        "api_key__secret_key",
        "api_key__password",
        "copy_setting__margin",
        "copy_setting__take_profit_percentage",
        "copy_setting__stop_loss_percentage",
        "position__side",
        "position__leverage",
        "position__amount",
        "position__symbol",
        "position__id",
    )
    data = dict(
        exchange=exchange,
        action="close_position_copy_orders",
        subscribers=list(subscribers_data),
        sandbox_mode=settings.CCXT_SANDBOX_MODE,
    )
    process_result = build_subprocess(stdin=json.dumps(data, default=decimal_default))
    copy_trading_results_logger.debug(process_result)
    celery_logger.debug(process_result)
    reduce_only_orders = []
    if position.side == PositionSideChoice.LONG:
        order_opposite_side = OrderSideChoices.SELL
    else:
        order_opposite_side = OrderSideChoices.BUY
    for subscriber_result in json.loads(process_result):
        if not subscriber_result["ok"]:
            submission_error = subscriber_result["result"]["exception_detail"]
            state = TradingOrderStatusChoices.FAILED
        else:
            submission_error = None
            state = TradingOrderStatusChoices.OPPOSE_SIDE_MARKET_CLOSE
        reduce_only_orders.append(
            TradingOrder(
                parent_order_id=parent_order_id,
                profile=position.profile,
                order_id=subscriber_result["result"]["id"],
                service=position.service,
                exchange=exchange,
                symbol=position.symbol,
                coin_pair=coin_pair,
                side=order_opposite_side,
                state=state,
                reduce_only=True,
                amount=position.amount,
                order_type=OrderTypeChoices.MARKET,  # TODO: Add LIMIT later
                type=TradingOrderType.FUTURES,  # TODO: SPOT in far future maybe!
                position_id=subscriber_result["subscriber_data"]["position__id"],
                submission_error=submission_error,
            )
        )
        try:
            position_to_close = Position.objects.get(id=subscriber_result["subscriber_data"]["position__id"])
            position_to_close.status = PositionStatusChoices.CLOSED
            position_to_close.closed_pnl_percentage = position.closed_pnl_percentage_calc
            position_to_close.save()
        except Exception as e:
            print(e,'===========position save')
    TradingOrder.objects.bulk_create(reduce_only_orders)


class Exchange:
    def __init__(
            self,
            exchange_name: str,
            api_key: str,
            secret: str,
            set_sandbox_mode: bool = settings.SET_SANDBOX_MODE,
            *args,
            **kwargs

    ):
        exchange_class = getattr(ccxt, exchange_name.lower())
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            **kwargs
        })
        if exchange_name in ['bybit','kucoin']:
            self.exchange.set_sandbox_mode(True)
        self.exchange.options["defaultType"] = 'future'


@app.task(name="fetch_vendor_balance")
def fetch_vendor_balance():
    service_owner_list = Service.objects.filter(service_type=ServiceTypeChoices.COPY).values_list('profile', flat=True)
    api_keys = ApiKey.objects.filter(owner_id__in=service_owner_list)
    for key in api_keys:
        obj = Exchange(
            exchange_name=key.exchange,
            api_key=key.api_key,
            secret=key.secret_key,
            password=key.password
        )
        try:
            balance = obj.exchange.fetch_balance().get('total')
            key.owner.services.filter(service_type=ServiceTypeChoices.COPY).update(balance=balance['USDT'])
        except Exception as e:
            print(e)
