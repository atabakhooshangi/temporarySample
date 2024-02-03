import decimal
import json
import logging
from django.utils.translation import gettext_lazy as _
from typing import Literal, Union
from datetime import datetime
from decimal import Decimal
import ccxt

from copytrading import exceptions
from copytrading.exceptions import InsufficientFundsException, NetworkErrorException, CCXTException, BingXErrorMsg
from copytrading.exchange.base import AbstractExchangeClient
from core.choice_field_types import PositionStatusChoices
from signals.exceptions import OrderIsNotFound

logger = logging.getLogger(__name__)


class BingX(AbstractExchangeClient):

    def get_balance(self, coin: str = "USDT", trade_type: str = 'future'):
        balance = 0
        try:
            balance = self.exchange.swap_v2_private_get_user_balance()['data']['balance']['balance']

        except Exception as e:
            logger.info(
                '{}  :: Throw an {} exception when attempting to get the balance {}'.format(
                    e,
                    datetime.now(),
                    self.exchange.apiKey
                )
            )
        except ccxt.ExchangeError as c:
            message = exceptions.FetchCCXTTextException().fetch_exception(message=c.args[0])
            logger.exception('{} :: Throw an {} exception attempting to get the balance of apikey {}'.format(
                datetime.now(),
                message,
                self.exchange.apiKey
            )
            )
        return balance

    def get_amount(self, amount: float):
        return amount

    def get_ccxt_response_order_id(self, ccxt_response):
        return ccxt_response["id"]

    @staticmethod
    def amount_modifier(amount, price, leverage):
        # TODO: compare decimal number with exchange ticker
        return (decimal.Decimal(amount) * decimal.Decimal(leverage)) / decimal.Decimal(price)

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
        amount = self.amount_modifier(amount, price, leverage)
        position_side = {"buy": "LONG", "sell": "SHORT"}
        params = {
            'positionSide': position_side[side],
            'timeInForce': "GTC",
            'takeProfit': float(take_profit) if take_profit is not None else None,
            'stopLoss': float(stop_loss) if stop_loss is not None else None,
            # 'reduceOnly': reduce_only # NOTE: this is causing error(In the Hedge mode, the 'ReduceOnly' field can not be filled.)
        }
        if reduce_only:
            params['reduceOnly'] = True
        leverage_keys = {
            'buy': 'longLeverage',
            'sell': 'shortLeverage'
        }
        filtered_params = {key: value for key, value in params.items() if value is not None}
        try:
            current_leverage = self.fetch_leverage(symbol)[leverage_keys[side]]
            if int(current_leverage) != int(leverage):
                self.set_leverage(symbol, int(leverage), position_side[side])
            return self.exchange.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                amount=amount,
                price=price,
                params=filtered_params,
            )
        except ccxt.InsufficientFunds:
            raise InsufficientFundsException
        except ccxt.NetworkError:
            raise NetworkErrorException
        except Exception as e:
            msg, data, is_error = BingXErrorMsg().handle_error(original_msg=e.args[0],
                                                               price=price,
                                                               take_profit=take_profit,
                                                               stop_loss=stop_loss
                                                               )
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                logger.exception("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)
                pass

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
            subscriber_data: dict = None,
    ):
        amount = self.amount_modifier(amount, price, leverage)
        position_side = {"buy": "LONG", "sell": "SHORT"}
        params = {
            'positionSide': position_side[side],
            'timeInForce': "GTC",
            'takeProfit': float(take_profit) if take_profit is not None else None,
            'stopLoss': float(stop_loss) if stop_loss is not None else None,
            # 'reduceOnly': reduce_only
        }
        if reduce_only:
            params['reduceOnly'] = True
        leverage_keys = {
            'buy': 'longLeverage',
            'sell': 'shortLeverage'
        }
        filtered_params = {key: value for key, value in params.items() if value is not None}
        try:
            # current_leverage = self.fetch_leverage(symbol)[leverage_keys[side]]
            # if int(current_leverage) != int(leverage):
            #     self.set_leverage(symbol, int(leverage), position_side[side])
            current_leverage = await self.async_fetch_leverage(symbol)
            current_leverage = current_leverage[leverage_keys[side]]
            subscriber_data['leverage'] = current_leverage
            if int(current_leverage) != int(leverage):
                await self.async_set_leverage(symbol, int(leverage), position_side[side])
            result = await self.async_exchange.create_order(
                symbol=symbol,
                side=side,
                type='limit',
                amount=amount,
                price=price,
                params=filtered_params,
            )
            await self.async_exchange.close()
            return dict(
                ok=True,
                result=result,
                subscriber_data=subscriber_data
            )
        except Exception as exc:
            return dict(
                ok=False,
                result=dict(exception_detail=exc.args[0]),
                subscriber_data=subscriber_data
            )

    def set_leverage(self, symbol: str, leverage: int, side: str):
        return self.exchange.set_leverage(leverage, symbol, {"side": side})

    async def async_set_leverage(self, symbol: str, leverage: int, side: str):
        res = await self.async_exchange.set_leverage(leverage, symbol, {"side": side})
        await self.async_exchange.close()
        return res

    def fetch_leverage(self, symbol: str):
        return self.exchange.fetch_leverage(symbol)['data']

    async def async_fetch_leverage(self, symbol: str):
        res = await self.async_exchange.fetch_leverage(symbol)
        await self.async_exchange.close()
        return res['data']

    def cancel_future_order(self, order_id: str, symbol: str):
        return self.exchange.cancel_order(order_id, symbol)

    async def async_cancel_future_order(self, order_id: str, symbol: str):
        try:
            result = await self.async_exchange.cancel_order(order_id, symbol)
            await self.async_exchange.close()
            return dict(
                ok=True,
                result=result,
                order_id=order_id
            )

        except Exception as exc:

            return dict(
                ok=False,
                result=dict(exception_detail=exc.args[0]),
                order_id=order_id
            )

    def get_order(self, order_id: str, symbol: str = None):
        return self.exchange.fetch_order(order_id, symbol)



    @staticmethod
    def search_order(data: list, search_param: Literal['TAKE_PROFIT', 'TAKE_PROFIT_MARKET', 'STOP', 'STOP_MARKET'], keyword: str):
        return list(filter(lambda x: search_param in x['info'][keyword], data))

    def cancel_open_order(self, order_id, symbol: str):
        return self.exchange.cancel_order(order_id, symbol)

    async def async_cancel_open_order(self, order_id, symbol: str):
        return await self.async_exchange.cancel_order(order_id, symbol)

    def cancel_all_open_orders(self, symbol):
        return self.exchange.cancel_all_orders(symbol)

    async def async_cancel_all_open_orders(self, symbol):
        return await self.async_exchange.cancel_all_orders(symbol)

    def create_take_profit_or_stop_order(self, symbol, side, amount, price, order_type: Literal['TAKE_PROFIT_MARKET', 'STOP_MARKET']):
        position_side = {"LONG": "buy", "SHORT": "sell"}
        params = {
            "stopPrice": price,
            'positionSide': side,
        }
        return self.exchange.create_order(
            symbol=symbol,
            side=position_side[side],
            type=order_type,
            amount=amount,
            price=price,
            params=params,
        )

    async def async_create_take_profit_or_stop_order(self, symbol, side, amount, price, order_type: Literal['TAKE_PROFIT_MARKET', 'STOP_MARKET']):
        position_side = {"LONG": "buy", "SHORT": "sell"}
        params = {
            "stopPrice": price,
            'positionSide': side,
        }
        return await self.async_exchange.create_order(
            symbol=symbol,
            side=position_side[side],
            type=order_type,
            amount=amount,
            price=price,
            params=params,
        )

    def edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        side = kwargs.get('side')
        amount = kwargs.get('amount')
        if None not in [take_profit, stop_loss]:
            cancel_response = self.cancel_all_open_orders(symbol)
            # if cancel_response['code'] != 0:
            #     raise Exception(f"error code : {cancel_response['code']} , message : {cancel_response['msg']}")
            take_profit_order = self.create_take_profit_or_stop_order(symbol, side, amount, take_profit, "TAKE_PROFIT_MARKET")
            stop_order = self.create_take_profit_or_stop_order(symbol, side, amount, stop_loss, "STOP_MARKET")
            return take_profit_order, stop_order
        open_orders = self.exchange.fetch_open_orders(symbol=symbol)
        if take_profit is not None:
            take_profit_order = self.search_order(open_orders, "TAKE_PROFIT", "type")
            if len(take_profit_order) > 0:
                self.cancel_open_order(take_profit_order[0]['info']['orderId'], symbol)

            take_profit_order = self.create_take_profit_or_stop_order(symbol, side, amount, take_profit, "TAKE_PROFIT_MARKET")
            return take_profit_order
        if stop_loss is not None:
            stop_order = self.search_order(open_orders, "STOP", "type")
            if len(stop_order) > 0:
                self.cancel_open_order(stop_order[0]['info']['orderId'], symbol)
            stop_order = self.create_take_profit_or_stop_order(symbol, side, amount, stop_loss, "STOP_MARKET")
            return stop_order

    async def async_edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        try:
            side = kwargs.get('side')
            amount = kwargs.get('amount')
            logger.info(f"{amount}-----,{side}")
            if None not in [take_profit, stop_loss]:
                cancel_response = await self.async_cancel_all_open_orders(symbol)
                # if cancel_response['code'] != 0:
                #     raise Exception(f"error code : {cancel_response['code']} , message : {cancel_response['msg']}")
                take_profit_order = await self.async_create_take_profit_or_stop_order(symbol, side, amount, take_profit, "TAKE_PROFIT_MARKET")
                stop_order = await self.async_create_take_profit_or_stop_order(symbol, side, amount, stop_loss, "STOP_MARKET")
                return take_profit_order, stop_order
            open_orders = await self.async_exchange.fetch_open_orders(symbol=symbol)
            if take_profit is not None:
                take_profit_order = self.search_order(open_orders, "TAKE_PROFIT", "type")
                if len(take_profit_order) > 0:
                    await self.async_cancel_open_order(take_profit_order[0]['info']['orderId'], symbol)

                take_profit_order = await self.async_create_take_profit_or_stop_order(symbol, side, amount, take_profit, "TAKE_PROFIT_MARKET")
                return take_profit_order
            if stop_loss is not None:
                stop_order = self.search_order(open_orders, "STOP", "type")
                if len(stop_order) > 0:
                    await self.async_cancel_open_order(stop_order[0]['info']['orderId'], symbol)
                stop_order = await self.async_create_take_profit_or_stop_order(symbol, side, amount, stop_loss, "STOP_MARKET")
                return stop_order
        except Exception as e:
            return {"params": {}, "error": e.args, }

        pass

    def close_position(self, position):

        params = {
            'positionSide': position.side.upper(),
            'timeInForce': "GTC",
            'reduceOnly': False
        }
        # for oppose side leverage we give short for longleverage and long for shortleverage
        leverage_keys = {
            'SHORT': 'longLeverage',
            'LONG': 'shortLeverage'
        }
        try:
            current_leverage = self.fetch_leverage(position.symbol)
            current_leverage = current_leverage[leverage_keys[position.side.upper()]]
            if int(current_leverage) != int(position.leverage):
                self.set_leverage(position.symbol, int(position.leverage), position.side.upper())
            result = self.exchange.create_order(
                symbol=position.symbol,
                side='buy' if position.side.upper() == 'SHORT' else 'sell',
                type="market",
                amount=position.amount,
                params=params,
            )
            return result
        except Exception as e:
            raise e

    async def async_close_position(self,
                                   position: dict,
                                   subscriber_data: dict = None):
        params = {
            'positionSide': position.get('side').upper(),
            'timeInForce': "GTC",
            'reduceOnly': False
        }
        # for oppose side leverage we give short for longleverage and long for shortleverage
        leverage_keys = {
            'SHORT': 'longLeverage',
            'LONG': 'shortLeverage'
        }
        try:
            current_leverage = await self.async_fetch_leverage(position.get('symbol'))
            current_leverage = current_leverage[leverage_keys[position.get('side').upper()]]
            if int(current_leverage) != int(position.get('leverage')):
                await self.async_set_leverage(position.get('symbol'), int(position.get('leverage')), position.get('side').upper())
            result = await self.async_exchange.create_order(
                symbol=position.get('symbol'),
                side='buy' if position.get('side').upper() == 'SHORT' else 'sell',
                type="market",
                amount=position.get('amount'),
                params=params,
            )

            return dict(
                ok=True,
                result=result,
                subscriber_data=subscriber_data
            )
        except Exception as exc:
            return dict(
                ok=False,
                result=dict(exception_detail=exc.args[0]),
                subscriber_data=subscriber_data
            )

    def get_positions(self, symbol: list):
        positions = self.exchange.fetch_positions(symbol)
        if len(positions) == 1:
            return positions[0]
        return {'side': None}  # to match get_positions output with other exchanges

    def get_futures_closed_pnl_list(self, symbol):
        pass

    def fetch_closed_orders(self, symbol):
        return self.exchange.fetch_closed_orders(symbol)

    @staticmethod
    def generate_updated_position_data(position_data: dict):
        return {

            'amount': position_data.get('info')['positionAmt'],
            'side': position_data.get('side').upper(),
            'unrealised_pnl': position_data.get('unrealizedPnl'),
            'avg_entry_price': position_data.get('entryPrice'),
            'leverage': int(position_data.get('leverage')),
            'take_profit': position_data.get('takeProfitPrice'),
            'stop_loss': position_data.get('stopLossPrice'),
            'liquidation_price': Decimal(
                position_data.get('liquidationPrice')) if position_data.get(
                'liquidationPrice') is not None else None,

        }

    def update_closed_position(self, position, update_data: dict, **kwargs):
        order_id = kwargs['response']['info']['orderId']
        closing_order = self.get_order(order_id, position.symbol)
        update_data['status'] = PositionStatusChoices.CLOSED
        update_data['avg_exit_price'] = Decimal(closing_order['info']['avgPrice'])
        update_data['updated_at'] = datetime.now()
        update_data['closed_datetime'] = datetime.fromtimestamp(
            int(str(closing_order.get('info')['updateTime'])[:10]))
        position.update_model_instance(**update_data)
        return update_data

    def edit_order(self, *args, **kwargs):
        price = kwargs.get('price')
        stop_loss = kwargs.get('stop_loss')
        take_profit = kwargs.get('take_profit')
        try:
            self.cancel_open_order(order_id=kwargs.pop('order_id'), symbol=kwargs.get('symbol'))
            new_order = self.create_future_order(
                **kwargs
            )
            return new_order
        except ccxt.InsufficientFunds:
            raise InsufficientFundsException
        except ccxt.NetworkError:
            raise NetworkErrorException
        except Exception as e:
            msg, data, is_error = BingXErrorMsg().handle_error(original_msg=e.args[0],
                                                               price=price,
                                                               take_profit=take_profit,
                                                               stop_loss=stop_loss
                                                               )
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                print("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)

    def fetch_order(
            self,
            order_id: str,
            symbol: str
    ):

        orders = self.exchange.fetch_open_orders(symbol)
        if len(orders) == 0:
            raise OrderIsNotFound
        for order in orders:
            if order['info']['orderId'] == order_id:
                return order
        raise OrderIsNotFound

    def get_closed_orders(self,
                          symbol: str):

        return self.exchange.fetch_closed_orders(symbol=symbol)
