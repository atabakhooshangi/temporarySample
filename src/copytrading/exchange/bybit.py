import decimal
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Literal

import ccxt

from copytrading import exceptions
from copytrading.exchange.base import AbstractExchangeClient
from copytrading.exchange_exception import ExchangeMessageText
from core.choice_field_types import PositionStatusChoices
from core.message_text import MessageText
from signals.exceptions import OrderIsNotFound

logger = logging.getLogger(__name__)


class Bybit(AbstractExchangeClient):

    def get_balance(self, coin: str = "USDT", trade_type: str = 'future'):
        self.exchange.options["defaultType"] = None
        asset = 0
        # When set to future , the result is waaaaay different from what it should be!!!! Death to bybit v5 update
        try:
            result = self.exchange.fetch_balance(params={'type': trade_type}).get('total')
            print("BALANCE OBJECT:", result)
            if coin.upper() in result.keys():
                asset = result[coin.upper()]
        except Exception as e:
            logger.error(
                '{}  :: Throw an {} exception when attempting to get the balance {}'.format(
                    e,
                    datetime.now(),
                    self.exchange.apiKey
                )
            )
        except ccxt.AuthenticationError:
            logger.error('{}  :: Throw an exception : {} \n attempting to get the balance of apikey : {}'.format(
                datetime.now(),
                MessageText.AuthenticationError500,
                self.exchange.apiKey
            ))
            raise exceptions.ExchangeAuthenticationError
        except ccxt.ExchangeError as e:
            message = exceptions.FetchCCXTTextException().fetch_exception(message=e.args[0])  # TODO:FIX SYMBOL
            logger.exception('{} :: Throw an {} exception attempting to get the balance of apikey {}'.format(
                datetime.now(),
                message,
                self.exchange.apiKey
            )
            )
        return asset

    def get_amount(self, amount: float):
        return amount

    def get_ccxt_response_order_id(self, ccxt_response):
        return ccxt_response["id"]

    def get_order(self, order_id: str, symbol: str = None):
        return self.exchange.fetch_order(order_id)

    @staticmethod
    def amount_modifier(amount, price, leverage):
        # TODO: compare decimal number with exchange ticker
        return (decimal.Decimal(amount) * decimal.Decimal(leverage)) / decimal.Decimal(price)

    def is_unified(self):
        enableUnifiedMargin, enableUnifiedAccount = self.exchange.is_unified_enabled()
        return enableUnifiedAccount, enableUnifiedMargin

    async def async_is_unified(self):
        enableUnifiedMargin, enableUnifiedAccount = await self.async_exchange.is_unified_enabled()
        return enableUnifiedAccount, enableUnifiedMargin

    def set_leverage(self,
                     symbol,
                     leverage):
        try:
            set_leverage_result = self.exchange.set_leverage(leverage, symbol)
        except ccxt.InsufficientFunds:
            raise exceptions.InsufficientFundsException
        except ccxt.AuthenticationError:
            raise exceptions.ExchangeAuthenticationError
        except ccxt.NetworkError as e:
            raise exceptions.NetworkErrorException
        except ccxt.ExchangeError as e:
            exception_obj = exceptions.ByBitErrorMsg()
            msg, data, is_error = exception_obj.fetch_bybit_exception(message=e.args[0])
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                logger.exception("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)
                pass

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
        # position_index = {"buy": 1, "sell": 2}
        # enableUnifiedMargin, enableUnifiedAccount = self.is_unified()
        # print(enableUnifiedAccount, '===============================')
        # params = {
        #     'leverage': leverage,
        #     'takeProfit': take_profit,
        #     'stopLoss': stop_loss,
        #     'reduceOnly': reduce_only,
        #     'positionIdx': position_index[side] if enableUnifiedAccount else 0
        # }
        self.set_leverage(symbol, leverage)
        try:
            enableUnifiedMargin, enableUnifiedAccount = self.exchange.is_unified_enabled()
            if enableUnifiedAccount:
                # Don't work this type
                position_index = {"buy": 1, "sell": 2}
                params = {
                    'leverage': leverage,
                    'takeProfit': take_profit if take_profit is not None else None,
                    'stopLoss': stop_loss if stop_loss is not None else None,
                    'reduceOnly': reduce_only,
                }
                customTimestamp = self.exchange.fetch_time()
                self.exchange.options['customTimestamp'] = customTimestamp
            else:
                params = {
                    'takeProfit': take_profit if take_profit is not None else None,
                    'stopLoss': stop_loss if stop_loss is not None else None,
                    'reduceOnly': reduce_only
                }
            filtered_params = {key: value for key, value in params.items() if value is not None}
            return self.exchange.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                amount=amount,
                price=price,
                params=filtered_params,
            )
        except ccxt.InsufficientFunds:
            raise exceptions.InsufficientFundsException
        except ccxt.AuthenticationError:
            raise exceptions.ExchangeAuthenticationError
        except ccxt.NetworkError as e:
            raise exceptions.NetworkErrorException
        except Exception as e:
            exception_obj = exceptions.ByBitErrorMsg()
            msg, data, is_error = exception_obj.fetch_bybit_exception(message=e.args[0], price=price,
                                                                      take_profit=take_profit,
                                                                      stop_loss=stop_loss
                                                                      )
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                print("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)

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
        amount = self.amount_modifier(amount, price, leverage)
        position_index = {"buy": 1, "sell": 2}
        enableUnifiedMargin, enableUnifiedAccount = await self.async_is_unified()
        try:
            params = {
                'takeProfit': take_profit if take_profit is not None else None,
                'stopLoss': stop_loss if stop_loss is not None else None,
                'reduceOnly': reduce_only,
                'positionIdx': position_index[side] if enableUnifiedAccount else 0
            }
            self.set_leverage(symbol, leverage)
            try:
                self.set_leverage(symbol, leverage)
            except ccxt.ExchangeError as e:
                message = exceptions.FetchCCXTTextException().fetch_exception(message=e.args[0], symbol=symbol)
                raise exceptions.CCXTException(detail=message)
            except Exception as e:
                raise e
            filtered_params = {key: value for key, value in params.items() if value is not None}
            result = await self.async_exchange.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
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

    def cancel_future_order(
            self,
            order_id: str,
            symbol: str
    ):
        try:
            return self.exchange.cancel_order(order_id, symbol)
        except ccxt.AuthenticationError:
            raise exceptions.ExchangeAuthenticationError
        except ccxt.NetworkError as e:
            raise exceptions.NetworkErrorException
        except ccxt.ExchangeError as e:
            exception_obj = exceptions.ByBitErrorMsg()
            msg, data, is_error = exception_obj.fetch_bybit_exception(message=e.args[0])
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                print("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)

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

    def fetch_order(
            self,
            order_id: str,
            symbol: str
    ):
        orders = self.exchange.fetch_open_orders(symbol, params={'orderId': order_id})
        if len(orders) == 1:
            order = orders[0]
        else:
            raise OrderIsNotFound
        return order

    def close_position(self, position):
        params = {
            'leverage': position.leverage,
            'reduceOnly': True,
            'closeOrder': True,
        }
        opposite_side = "sell" if position.side.lower() == "long" else "buy"
        return self.exchange.create_market_order(
            symbol=position.symbol,
            side=opposite_side,
            amount=position.quantity,
            params=params,
        )

    async def async_close_position(
            self,
            position: dict,
            subscriber_data: dict = None
    ):
        params = {
            'leverage': position["leverage"],
            'reduceOnly': True,
            'closeOrder': True,
        }
        try:
            side = "buy" if position["side"].lower() == "short" else "sell"
            result = await self.async_exchange.create_market_order(
                symbol=position["symbol"],
                side=side,
                amount=position["amount"],
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
        exchange_position = self.exchange.fetch_positions(symbol)
        enableUnifiedMargin, enableUnifiedAccount = self.exchange.is_unified_enabled()
        if enableUnifiedAccount:
            exchange_position = [
                item for item in exchange_position
                if float(item['info']['avgPrice']) > 0 and float(item['info']['size']) > 0 and float(
                    item['info']['positionValue']) > 0]
            exchange_position = exchange_position[0]
        else:
            exchange_position = exchange_position[0]
        return exchange_position

    def get_position(self, symbol):
        return self.exchange.fetch_position(
            symbol
        )

    # This method is temporary until bybit supports it
    # The reason to use this endpoint is , it doesn't need a symbol , it gives all pnl history in batch , but the one we have a symbol param is required to get called
    # So we need to call for each market we have and create a position history for them.
    def get_closed_pnl_in_batch(self):
        from pybit.unified_trading import HTTP
        session = HTTP(
            testnet=True,
            api_key=self.exchange.apiKey,
            api_secret=self.exchange.secret,
        )
        return session.get_closed_pnl(
            category="linear",
        )

    def get_futures_closed_pnl_list(
            self,
            symbol,
            cursor
    ):
        while True:
            try:
                return self.exchange.privateGetContractV3PrivatePositionClosedPnl(
                    {
                        'symbol': symbol,
                        'cursor': cursor
                    }
                )
            except Exception as e:
                print(e)
                logger.info(f'==== get {type(e)} exception in fetch closed position function. =====')
                time.sleep(3)
                continue

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
        # function arguments are the same for unified and the other account type,at this time.
        # params = dict()
        # if take_profit is not None:
        #     params['takeProfit'] = take_profit
        # if stop_loss is not None:
        #     params['stopLoss'] = stop_loss
        try:
            self.cancel_future_order(order_id, symbol)
            return self.create_future_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                amount=amount,
                price=price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                leverage=leverage,
            )
            # amount = self.amount_modifier(amount, price, leverage)
            # if 'takeProfit' in params or 'stopLoss' in params:
            #     self.exchange.edit_order(
            #         id=order_id,
            #         symbol=symbol,
            #         side=side,
            #         type=order_type,
            #         price=None,
            #         amount=None,
            #         params=params
            #     )
            # return self.exchange.edit_order(
            #     id=order_id,
            #     symbol=symbol,
            #     side=side,
            #     type=order_type,
            #     price=price,
            #     amount=amount,
            #     # params=params
            # )
        except ccxt.InsufficientFunds:
            raise exceptions.InsufficientFundsException
        except ccxt.AuthenticationError:
            raise exceptions.ExchangeAuthenticationError
        except ccxt.NetworkError as e:
            raise exceptions.NetworkErrorException
        except Exception as e:
            exception_obj = exceptions.ByBitErrorMsg()
            msg, data, is_error = exception_obj.fetch_bybit_exception(message=e.args[0], price=price)
            if is_error:
                raise exceptions.CCXTException(detail=msg)
            else:
                print("result of parsing error passed:", "msg:", msg, "data:", data, "is_error:", is_error)

    def edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        if '/' in symbol or ':' in symbol:
            coin, pair = symbol.split('/')
            pair = pair.split(':')[0]
            symbol = f"{coin}{pair}"
        params = {
            'category': "linear",
            'symbol': symbol,
            'positionIdx': 0
        }
        if take_profit:
            params['takeProfit'] = str(take_profit)
        if stop_loss:
            params['stopLoss'] = str(stop_loss)
        return self.exchange.privatePostV5PositionTradingStop(params)

    async def async_edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        try:
            if '/' in symbol or ':' in symbol:
                coin, pair = symbol.split('/')
                pair = pair.split(':')[0]
                symbol = f"{coin}{pair}"
            params = {
                'category': "linear",
                'symbol': symbol,
                'positionIdx': 0
            }
            if take_profit:
                params['takeProfit'] = str(take_profit)
            if stop_loss:
                params['stopLoss'] = str(stop_loss)
            return self.exchange.privatePostV5PositionTradingStop(params)
        except Exception as e:
            return {"params": params, "error": e.args, }

    def fetch_closed_orders(self, symbol):
        return self.exchange.fetch_closed_orders(symbol)

    @staticmethod
    def generate_updated_position_data(position_data: dict):
        return {
            'created_at': datetime.fromtimestamp(
                int(str(position_data.get('timestamp'))[:10])),
            'updated_at': datetime.fromtimestamp(
                int(str(position_data.get('info')['updatedTime'])[:10])),
            'value': position_data.get('info')['positionValue'] if position_data.get(
                'side') is not None else None,
            'quantity': position_data.get('info')['size'] if position_data.get(
                'side') is not None else None,
            'unrealised_pnl': position_data.get('unrealizedPnl'),
            'avg_entry_price': position_data.get('entryPrice'),
            'leverage': int(position_data.get('leverage')),
            'take_profit': Decimal(
                position_data.get('info')['takeProfit']),
            'stop_loss': Decimal(
                position_data.get('info')['stopLoss']),
            'liquidation_price': Decimal(
                position_data.get('liquidationPrice')) if position_data.get(
                'liquidationPrice') is not None else None,

        }

    def update_closed_position(self, position, update_data: dict, **kwargs):
        # closed_positions = self.get_futures_closed_pnl_list(f"{kwargs['coin']}{kwargs['pair']}").get('result').get(
        #     'list')
        # closed_orders = self.fetch_closed_orders(
        #     position.symbol
        # )
        match_order = False
        match_position = False
        closed_positions = None
        closed_orders = list()
        while not match_order:
            closed_orders = self.exchange.fetch_closed_orders(position.symbol, params={
                'cursor': closed_orders[-1].get('info').get('nextPageCursor') if len(closed_orders) != 0 else None})
            if len(closed_orders) != 0:
                for closed_order in closed_orders[::-1]:
                    try:
                        if Decimal(closed_order.get('amount')).quantize(Decimal('1.000')) == Decimal(
                                position.quantity).quantize(Decimal('1.000')) and closed_order.get(
                            'side').lower() != position.side.lower():
                            exchange_order_id = closed_order.get('id')
                            match_order = True
                            while not match_position:
                                closed_positions = self.get_futures_closed_pnl_list(
                                    symbol=f"{kwargs['coin']}{kwargs['pair']}", cursor=closed_positions.get(
                                        'nextPageCursor') if closed_positions is not None else None).get('result')
                                if len(closed_positions.get('list')) != 0:
                                    for ps in closed_positions.get('list'):
                                        if ps.get('orderId') == exchange_order_id:
                                            update_data['status'] = PositionStatusChoices.CLOSED
                                            update_data['closed_pnl'] = Decimal(ps.get('closedPnl'))
                                            update_data['avg_entry_price'] = Decimal(ps.get('avgEntryPrice'))
                                            update_data['avg_exit_price'] = Decimal(ps.get('avgExitPrice'))
                                            update_data['closed_pnl_percentage'] = (Decimal(ps.get('closedPnl')) / (
                                                    Decimal(position.value) *
                                                    Decimal(position.leverage))) * 100
                                            update_data['closed_datetime'] = datetime.fromtimestamp(
                                                int(str(ps.get('updatedTime'))[:10]))
                                            position.update_model_instance(**update_data)
                                            match_position = True
                                            return update_data
                                        else:
                                            continue
                                else:
                                    break

                        else:
                            continue
                    except Exception as e:
                        logger.debug(e)
            else:
                match_order = True  # Note: Matching order with the position is not happen, but should break the while
                # update_data['status'] = PositionStatusChoices.X_CLOSED
                # position.update_model_instance(**update_data)
                # return update_data
        update_data['status'] = PositionStatusChoices.X_CLOSED
        position.update_model_instance(**update_data)
        return update_data
