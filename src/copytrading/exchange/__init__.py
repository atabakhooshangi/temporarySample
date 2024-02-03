from .base import AbstractExchangeClient  # noqa
from .bybit import Bybit  # noqa
from .kucoin import Kucoin  # noqa
from .bingx import BingX
from .nobitex import Nobitex

def generate_exchange_client(
        exchange: str,
        credentials: dict,
        sandbox_mode=False
) -> AbstractExchangeClient:
    exchange_name = exchange.lower()
    api_key = credentials["api_key"]
    secret = credentials["secret"] if 'secret' in credentials else None
    if exchange_name == "bybit":
        return Bybit(
            exchange_name="bybit",
            api_key=api_key,
            secret=secret,
            sandbox_mode=sandbox_mode,
        )

    elif exchange_name == "bingx":
        return BingX(
            exchange_name="bingx",
            api_key=api_key,
            secret=secret,
            sandbox_mode=sandbox_mode,
        )
    elif exchange_name == "kucoin":
        return Kucoin(
            exchange_name="kucoinfutures",
            api_key=api_key,
            secret=secret,
            sandbox_mode=sandbox_mode,
            exchange_options=dict(password=credentials["password"])
        )
    elif exchange_name == 'nobitex':
        return Nobitex(
            exchange_name="nobitex",
            api_key=api_key,
        )


