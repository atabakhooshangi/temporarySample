import decimal
import json
import logging
import re
import time
from datetime import datetime
from decimal import Decimal
from typing import Literal

import ccxt
import requests

from copytrading import exceptions
from copytrading.exceptions import CCXTException
from copytrading.exchange.base import AbstractExchangeClient
from copytrading.exchange_exception import ExchangeMessageText
from core.choice_field_types import PositionStatusChoices
from core.message_text import MessageText
from signals.exceptions import OrderIsNotFound
import os

logger = logging.getLogger(__name__)


class Nobitex(AbstractExchangeClient):

    def __init__(self, exchange_name, api_key):
        super().__init__(exchange_name=exchange_name, api_key=api_key)
        self.base_url = os.environ['NOBITEX_BASE_URL']
        self.headers = {
            'Authorization': f'TOKEN {self.api_key}',
            'Content-Type': 'application/json',
        }

    @staticmethod
    def amount_modifier(amount, price):
        # TODO: compare decimal number with exchange ticker
        return decimal.Decimal(amount) / decimal.Decimal(price)

    def get_balance(self, coin: str = "USDT", trade_type: str = 'future'):
        path = 'users/wallets/balance'
        nobitex_response = requests.post(
            url=self.base_url + path,
            headers=self.headers,
            data=json.dumps(dict(currency=coin.lower()))
        )
        response = json.loads(nobitex_response.text)
        if response.get('status') == 'failed':
            logger.exception(response)
            raise CCXTException(detail=response.get('message'))
        elif nobitex_response.status_code != 200:
            raise CCXTException(detail=response.get('detail'))

        elif response.get('status') == 'ok':
            return response.get('balance')

    def create_future_order(
            self,
            symbol: str,
            side: Literal['buy', 'sell'],
            order_type: Literal['limit', 'market'],
            amount,
            price,
            take_profit,
            stop_loss,
            leverage,
            reduce_only: bool = False
    ):
        amount = self.amount_modifier(amount, price)  # TODO: check the value with leverage or not
        src_currency_pattern = r'([^/]*)/'
        ds_currency_pattern = r'\/(.+)$'
        srcCurrency = re.search(src_currency_pattern, symbol).group(1)
        dstCurrency = re.search(ds_currency_pattern, symbol).group(1)
        request_data = dict(
            srcCurrency=srcCurrency.lower(),
            dstCurrency=dstCurrency.lower(),
            leverage=str(leverage),
            amount=str(amount),
            price=str(price),
            stopLimitPrice=str(take_profit),
            stopPrice=str(stop_loss),
            type=side
        )

        try:
            path = 'margin/orders/add'
            nobitex_response = requests.post(
                url=self.base_url + path,
                headers=self.headers,
                data=json.dumps(request_data)
            )
            response = json.loads(nobitex_response.text)
            if response.get('status') == 'failed':
                logger.exception(response)
                raise CCXTException(detail=response.get('message'))
            elif nobitex_response.status_code != 200:
                raise CCXTException(detail=response.get('detail'))

            elif response.get('status') == 'ok':
                return response.get('order')
        except Exception as e:
            raise e

    def cancel_future_order(
            self,
            order_id: str,
            symbol: str
    ):
        # At this date for this action there is not any api based this doc(https://apidocs.nobitex.ir/#a876cd1a69)
        raise NotImplemented

    # def get_balance(self, coin: str = "USDT", trade_type: str = 'future'):
    #     raise NotImplemented

    def get_amount(self, amount: float):
        return amount

    def get_ccxt_response_order_id(self, ccxt_response):
        print(ccxt_response)
        return ccxt_response["id"]

    def get_order(self, order_id: str, symbol: str = None):
        raise NotImplemented

    def is_unified(self):
        raise NotImplemented

    async def async_is_unified(self):
        raise NotImplemented
    def set_leverage(self,
                     symbol,
                     leverage):
        raise NotImplemented

    async def async_create_future_order(
            self,
            symbol: str,
            side: Literal['buy', 'sell'],
            order_type: Literal['limit', 'market'],
            amount,
            price,
            take_profit,
            stop_loss,
            leverage,
            reduce_only: bool = False,
            subscriber_data: dict = None,  # When using for subscriber
    ):
        raise NotImplemented

    async def async_cancel_future_order(self, order_id: str, symbol: str):
        # At this date for this action there is not any api based this doc(https://apidocs.nobitex.ir/#a876cd1a69)
        raise NotImplemented

    def fetch_order(
            self,
            order_id: str,
            symbol: str
    ):
        raise NotImplemented

    def close_position(self, position):
        raise NotImplemented

    async def async_close_position(
            self,
            position: dict,
            subscriber_data: dict = None
    ):
        raise NotImplemented

    def get_positions(self, symbol: list):
        raise NotImplemented

    def get_position(self, symbol):
        raise NotImplemented

    def get_closed_pnl_in_batch(self):
        raise NotImplemented

    def get_futures_closed_pnl_list(
            self,
            symbol,
            cursor
    ):
        raise NotImplemented

    def edit_order(self,
                   order_id,
                   symbol: str,
                   side: Literal['buy', 'sell'],
                   order_type: Literal['limit', 'market'],
                   price,
                   amount: None,
                   leverage,
                   take_profit: None,
                   stop_loss: None
                   ):
        raise NotImplemented
    def edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        raise NotImplemented

    async def async_edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        raise NotImplemented

    def fetch_closed_orders(self, symbol):
        raise NotImplemented


    def update_closed_position(self, position, update_data: dict, **kwargs):
        raise NotImplemented

