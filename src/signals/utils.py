import ccxt

from core.choice_field_types import TradingSignalType
from django.core.exceptions import MultipleObjectsReturned
from signals.models import ExchangeMarket


def market_fetcher():
    exchange_class = getattr(
        ccxt,
        "bingx"
    )
    bing: ccxt.bingx = exchange_class(
    )

    bingx_markets = bing.fetch_swap_markets({})
    added_bingx_markets = []
    for market in bingx_markets:
        m: ExchangeMarket = ExchangeMarket.objects.filter(base_currency=market['base'],
                                                          quote_currency=market['quote'],
                                                          exchange_name__icontains='bingx',
                                                          market_type=TradingSignalType.FUTURES)
        m.update(tick_size=market['contractSize'])
        if len(m) == 0:
            ExchangeMarket.objects.create(
                coin_pair=market['id'],
                exchange_name='bingx',
                tick_size=market['contractSize'],
                coin_name=market['base'],
                base_currency=market['base'],
                quote_currency=market['quote'],
                futures_symbol=market['symbol'],
                market_type=TradingSignalType.FUTURES,
            )
            added_bingx_markets.append(market['id'])
        if len(m) > 1:
            print(f"Please delete duplicated market in bingx: {market['base']}")
            # NOTE: the following code might cause problems, because there might be signals attached to the market
            # duplicated_markets = ExchangeMarket.objects.filter(base_currency=market['base'],
            #                                                    quote_currency=market['quote'],
            #                                                    exchange_name__icontains='bingx',
            #                                                    market_type=TradingSignalType.FUTURES)
            # for market_item in m[1:]:
            #     print(f"Duplicated market {market_item} deleted")
            #     market_item.delete()

    exchange_class = getattr(
        ccxt,
        "bybit"
    )
    bbit: ccxt.bybit = exchange_class(
    )
    bybit_markets = bbit.fetch_future_markets({"category": "linear"})
    added_bybit_markets = []
    for market in bybit_markets:
        if market['quote'] != 'USDT':
            continue
        m: ExchangeMarket = ExchangeMarket.objects.filter(base_currency=market['base'],
                                                          quote_currency=market['quote'],
                                                          exchange_name__icontains='bybit',
                                                          market_type=TradingSignalType.FUTURES)
        m.update(tick_size=market['precision']['amount'])
        if len(m) == 0:
            ExchangeMarket.objects.create(
                coin_pair=market['id'],
                exchange_name='bybit',
                tick_size=market['precision']['amount'],
                coin_name=market['base'],
                base_currency=market['base'],
                quote_currency=market['quote'],
                futures_symbol=market['symbol'],
                market_type=TradingSignalType.FUTURES,

            )
            added_bybit_markets.append(market['id'])
        if len(m) > 1:
            print(f"Please delete duplicated market in bybit: {market['base']}")
            # NOTE: the following code might cause problems, because there might be signals attached to the market
            # duplicated_markets = ExchangeMarket.objects.filter(base_currency=market['base'],
            #                                                    quote_currency=market['quote'],
            #                                                    exchange_name__icontains='bingx',
            #                                                    market_type=TradingSignalType.FUTURES)
            # for market_item in m[1:]:
            #     print(f"Duplicated market {market_item} deleted")
            #     market_item.delete()
    print(added_bingx_markets, "added bingx markets")
    print(added_bybit_markets, "added bybit markets")

    return "Done"