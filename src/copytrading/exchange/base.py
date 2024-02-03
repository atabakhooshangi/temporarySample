from abc import ABC, abstractmethod

import ccxt
import ccxt.async_support as async_ccxt

from copytrading.exchange.preload_markets_data.bingx_ccxt_markets_preload import BINGX_MARKETS
from copytrading.exchange.preload_markets_data.bybit_ccxt_markets_preload import BYBIT_MARKETS


class AbstractExchangeClient(ABC):

    def __init__(
            self,
            exchange_name: str,
            api_key: str,
            secret: str = None,
            sandbox_mode: bool = False,
            exchange_options=dict(),
    ):
        if secret is None:
            self.api_key = api_key
        else:
            exchange_class = getattr(
                ccxt,
                exchange_name
            )
            async_exchange_class = getattr(
                async_ccxt,
                exchange_name
            )
            self.exchange = exchange_class(
                {
                    'enableRateLimit': False,
                    'apiKey': api_key,
                    'secret': secret,
                    **exchange_options
                }
            )

            if exchange_name in ['bybit', 'kucoin', 'BYBIT', 'KUCOIN']:
                self.exchange.set_sandbox_mode(
                    sandbox_mode
                )
            self.async_exchange = async_exchange_class(
                {
                    'enableRateLimit': False,
                    'apiKey': api_key,
                    'secret': secret,
                    **exchange_options
                }
            )
            if exchange_name in ['bybit', 'kucoin', 'BYBIT', 'KUCOIN']:
                self.async_exchange.set_sandbox_mode(
                    sandbox_mode
                )
            self.exchange.options["defaultType"] = 'future'
            # preload data
            if exchange_name == "bybit":
                self.exchange.markets = BYBIT_MARKETS
            if exchange_name == "bingx":
                self.exchange.markets = BINGX_MARKETS
                # NOTE: supporting VST in sandbox mode
                if sandbox_mode:
                    for key, val in self.exchange.urls['api'].items():
                        if isinstance(val, str) and val.startswith('https://open-api'):
                            self.exchange.urls['api'][key] = val.replace('https://open-api',
                                                                         'https://open-api-vst')
                            self.async_exchange.urls['api'][key] = val.replace('https://open-api',
                                                                               'https://open-api-vst')
            self.exchange.load_markets()

    @abstractmethod
    def get_order(self, order_id: str, symbol: str = None):
        raise NotImplementedError

    @abstractmethod
    def set_leverage(self, symbol: str, leverage: int):
        raise NotImplementedError

    @abstractmethod
    def get_balance(self, coin: str = "USDT", trade_type: str = "future"):
        raise NotImplementedError

    @abstractmethod
    def get_amount(self, amount: float):
        raise NotImplementedError

    @abstractmethod
    def get_ccxt_response_order_id(self, ccxt_response):
        raise NotImplementedError

    @abstractmethod
    def create_future_order(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def async_create_future_order(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def async_edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        raise NotImplementedError

    # @abstractmethod
    # def cancel_future_order(self, *args, **kwargs):
    #     raise NotImplementedError

    @abstractmethod
    def cancel_future_order(self, *args, **kwargs):
        raise NotImplementedError

    def fetch_order(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def close_position(self, position):
        raise NotImplementedError

    @abstractmethod
    async def async_close_position(self, position: dict):
        raise NotImplementedError

    @abstractmethod
    def get_positions(self, symbol: list):
        raise NotImplementedError

    @abstractmethod
    def get_futures_closed_pnl_list(self, symbol, cursor):
        raise NotImplementedError

    @abstractmethod
    def edit_position(self, symbol, stop_loss=None, take_profit=None, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def fetch_closed_orders(self, symbol):
        raise NotImplementedError

    @abstractmethod
    def edit_order(self, *args, **kwargs):
        raise NotImplementedError
