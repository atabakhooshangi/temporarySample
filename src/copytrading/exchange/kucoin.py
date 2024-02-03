from typing import Literal
from copytrading.exchange.base import AbstractExchangeClient


class Kucoin(AbstractExchangeClient):

    def get_balance(self, coin="USDT"):
        return self.exchange.fetch_balance()[coin]

    # ccxt use lot unit for measurement of order amount
    # 1000 BTC lot means 1 BTC, 1 BTC lot means 0.001
    def get_amount(self, amount: float):
        return amount * 1000

    def get_ccxt_response_order_id(self, ccxt_response):
        return ccxt_response["info"]["data"]["orderId"]

    def get_order(self, order_id: str, symbol: str = None):
        return self.exchange.fetch_order(order_id)

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
        params = {
            'leverage': leverage,
            'reduceOnly': reduce_only,
        }
        return self.exchange.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price,
            params=params,
        )

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
            reduce_only: bool = False
    ):
        params = {
            'leverage': leverage,
            'reduceOnly': reduce_only,
        }
        return await self.async_exchange.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            amount=amount,
            price=price,
            params=params,
        )

    def cancel_future_order(self, *args, **kwargs):
        # TODO: implement later
        pass

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

    def close_position(self, position):
        params = {
            'leverage': position["leverage"],
            'reduceOnly': True,
            'closeOrder': True,
        }
        opposite_side = "sell" if position["side"].lower() == "long" else "buy"
        return self.async_exchange.create_market_order(
            symbol=position["symbol"],
            side=opposite_side,
            amount=position["amount"],
            params=params,
        )

    async def async_close_position(self, position):
        params = {
            'leverage': position["leverage"],
            'reduceOnly': True,
            'closeOrder': True,
        }
        opposite_side = "sell" if position["side"].lower() == "long" else "buy"
        return await self.async_exchange.create_market_order(
            symbol=position["symbol"],
            side=opposite_side,
            amount=position["amount"],
            params=params,
        )
