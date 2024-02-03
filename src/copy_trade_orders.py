import datetime

from dotenv import load_dotenv

load_dotenv("src/core/.env")
import logging
import json
import asyncio
import sys
from typing import Union
from copytrading.exchange import generate_exchange_client
from decimal import Decimal

copy_trade_orders_logger = logging.getLogger(__name__)

copy_trades_logger = logging.getLogger(__name__)


def get_take_profit(
        take_profit: Union[Decimal, None],
        user_percentage: Union[Decimal, None],
        entry: Decimal,
        leverage: int = 1
):
    if take_profit is None and user_percentage is None:
        copy_trades_logger.info(f'{datetime.datetime.now()} :: The take profit for this order hasn\'t been set.')
        return None
    if user_percentage:
        user_take_profit = entry + (((user_percentage / leverage) / 100) * entry)
        copy_trades_logger.info(f"{user_take_profit} -----------------user_take_profit \n \n")
        copy_trades_logger.debug(user_take_profit)
        return user_take_profit
    return take_profit


def get_stop_loss(
        stop_loss: Union[Decimal, None],
        user_percentage: Union[Decimal, None],
        entry: Decimal,
        leverage: int = 1
):
    if stop_loss is None and user_percentage is None:
        copy_trades_logger.info('nooooooooooooooone stop_loss \n \n')
        return None
    if user_percentage:
        user_stop_loss = entry - (((user_percentage / leverage) / 100) * entry)
        copy_trades_logger.info(f"{user_stop_loss} -----------------user_stop_loss \n \n")
        return user_stop_loss
    return stop_loss


async def main():
    """
    this script is ran as a subprocess in the copy trade celery task
    and subscribers data are passed with stdin. the process will send
    async requests to exchanges to submit positions for the subscribers
    asynchronous. the result of process will be sended to the task as
    stdout
    """
    stdin = sys.stdin.read()
    data = json.loads(stdin)
    exchange = data["exchange"]
    action = data["action"]
    request_list = []
    for subscriber_data in data["subscribers"]:
        exchange_client = generate_exchange_client(
            exchange=exchange,
            credentials=dict(
                api_key=subscriber_data["api_key__api_key"],
                secret=subscriber_data["api_key__secret_key"],
                password=subscriber_data["api_key__password"],
            ),
            sandbox_mode=data["sandbox_mode"],
        )
        if action == "create_copy_orders":
            user_tp = get_take_profit(
                data["order"]["take_profit"],
                subscriber_data["copy_setting__take_profit_percentage"],
                data["order"]["entry_point"],
                data["order"]["leverage"],
            )
            take_profit = data["order"]["take_profit"] if user_tp is None else user_tp
            # Modify this in the new ticker based copy trading
            amount = min(subscriber_data["copy_setting__margin"], float(data["order"]["amount"]))
            user_sl = get_stop_loss(
                data["order"]["stop_loss"],
                subscriber_data["copy_setting__stop_loss_percentage"],
                data["order"]["entry_point"],
                data["order"]["leverage"],

            )
            stop_loss = data["order"]["stop_loss"] if user_sl is None else user_sl
            request_list.append(
                exchange_client.async_create_future_order(
                    symbol=data["order"]["symbol"],
                    side=data["order"]["side"].lower(),
                    order_type=data["order"]["order_type"].lower(),
                    amount=float(amount),
                    price=data["order"]["entry_point"],
                    take_profit=take_profit,
                    stop_loss=stop_loss,
                    leverage=data["order"]["leverage"],
                    subscriber_data=subscriber_data,
                )
            )
        elif action == "close_position_copy_orders":
            position_data = dict(
                symbol=subscriber_data["position__symbol"],
                leverage=subscriber_data["position__leverage"],
                amount=subscriber_data["position__amount"],
                side=subscriber_data["position__side"],
            )
            if subscriber_data["position__amount"] is None and subscriber_data["position__id"] is None:
                continue
            request_list.append(
                exchange_client.async_close_position(
                    position=position_data,
                    subscriber_data=subscriber_data
                )
            )
        elif action == 'edit_subscribers_positions':
            edit_data = data.get('edit_params')
            edit_data['amount'] = subscriber_data["position__quantity"]
            request_list.append(
                exchange_client.async_edit_position(
                    **edit_data
                )
            )
        elif action == 'cancel_copy_orders':
            request_list.append(
                exchange_client.async_cancel_future_order(
                    subscriber_data.get('order__exchange_order_id', None),
                    subscriber_data.get('order__symbol', None),

                )
            )

    result = await asyncio.gather(*request_list)
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
