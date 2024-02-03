import datetime
import json
import logging

import requests
from django.conf import settings

from django_redis import get_redis_connection

from core.api_gateways import ProducerClientGateway, KafkaTopic
from core.celery import app
from monolithictasks.helpers import get_irt_price


logger = logging.getLogger(__name__)





@app.task(name='civil_registry')
def civil_registry():
    try:
        ProducerClientGateway().produce(KafkaTopic.CIVIL_REGISTRY_CREDENTIAL_VALIDATION_TOPIC, json.dumps({"data": "data"}))
    except Exception as e:
        print("========>", e)



    try:
        ProducerClientGateway().produce(KafkaTopic.CIVIL_REGISTRY_BANK_ACCOUNT_VALIDATION_TOPIC, json.dumps({"data": "data"}))
    except Exception as e:
        print("========>", e)

    return "Civil Registry and card Called!"


@app.task(name='irt_price_updater')
def irt_price_updater():
    irt_price = get_irt_price()

    with get_redis_connection("data_cache") as redis_conn:

        coins_dict = {'bitcoin': 'بیتکوین', 'binancecoin': "بایننس کوین", 'tron': 'ترون',
                      'ethereum': 'اتریوم', 'tether': 'تتر',
                      'dogecoin': 'دوج کوین', 'elrond-erd-2': 'ارلاند',
                      'chainlink': 'لینک', 'shiba-inu': 'شیبا', 'zcash': 'زیکش', 'uniswap': 'یونی سواپ',
                      'solana': 'سولانا', 'ripple': 'ریپل', 'polkadot': 'پولکادات', 'matic-network': 'ماتیک',
                      'filecoin': 'فایل کوین', 'fantom': 'فانتوم',
                      'dai': 'دای', 'axie-infinity': 'اکسی اینفینیتی', 'avalanche-2': 'آوالانچ', 'decentraland': 'مانا', 'injective-protocol': 'انجکتیو','cardano':'کاردانو'}

        ids = ','.join(
            ['bitcoin', 'binancecoin', 'tron', 'ethereum', 'tether',
             'dogecoin', 'elrond-erd-2', 'chainlink', 'shiba-inu', 'zcash', 'uniswap', 'solana',
             'ripple', 'polkadot', 'matic-network', 'filecoin', 'fantom', 'dai', 'axie-infinity', 'avalanche-2', 'decentraland', 'injective-protocol','cardano'])

        url = f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}'

        session = requests.Session()
        try:

            # current_price = get_irr_price()
            prices = session.get(url, timeout=13).json()


        except requests.exceptions.Timeout:
            print("timeout price update")
            return
        except requests.exceptions.TooManyRedirects:
            print("TooManyRedirects")
            return
        except requests.exceptions.RequestException:
            return
        if not isinstance(prices, list):
            return
        try:
            for price in prices:
                price['name_in_farsi'] = coins_dict[price['id']]
        except Exception as e:
            print(e)

        prices.append(
            {
                "id": "rial",
                "symbol": "USDIRR",
                "name": "rial",
                "name_in_farsi": "ریال",
                "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzJoTZ01QufKE1ZkAjPvvA6BZFGGdppPOMU-sD4tbUlDAjl7BgW_PQmJR1EGC0MI9UG3s&usqp=CAU",
                "current_price": irt_price,
                "market_cap": 0,
                "market_cap_rank": 0,
                "fully_diluted_valuation": 0,
                "total_volume": 0,
                "high_24h": 0,
                "low_24h": 0,
                "price_change_24h": 0,
                "price_change_percentage_24h": 0,
                "market_cap_change_24h": 0,
                "market_cap_change_percentage_24h": 0,
                "circulating_supply": 0,
                "total_supply": 0,
                "max_supply": 0,
                "ath_change_percentage": 0,
                "ath_date": "2020-12-20T00:00:00.000Z",
                "atl": 3,
                "atl_change_percentage": 800,
                "atl_date": "1990-12-16T00:00:00.000Z",
                "roi": None,
                "last_updated": "1990-12-16T00:00:00.000Z"
            },
        )
        irt_price_dict = {"current_price": irt_price}
        redis_conn.set(name="irt_price", value=json.dumps(irt_price_dict, indent=2))

        redis_conn.set(name="prices", value=json.dumps(prices))

    try:
        with requests.session() as session:
            headers = {
                "Content-Type": "application/json",
                "X-EXWINO-API": settings.ACCOUNTING_API_KEY,
            }
            response = session.request('GET',
                                       f"{settings.ACCOUNTING_URL}{settings.API_V1_STR}/admin/prices/update_prices/",
                                       headers=headers, params={}, timeout=15)
        print(response.status_code)
    except Exception as e:
        print(f"error with sending persist prices request :  Error {e.args[0]}")
        logger.info(f"error with sending persist prices request :  Error {e.args[0]}")

    return "persist prices Called!"

@app.task(name='bybit_price_cacher')
def bybit_price_cacher():
        with get_redis_connection("data_cache") as redis_conn:
            try:
                url_coin = f"{settings.CONFIG_SERVER_BASE_URL}exchange/coins/?recurse=true"
                coins = requests.get(url_coin, {"recurse": True}, timeout=7).json()
                coin_list = [x['Key'].split('/')[-1].upper() for x in coins]
                url = "https://api.bybit.com/v5/market/tickers?category=spot"

                price_data = requests.get(url=url, timeout=6)
                print('=======status',price_data.status_code)
                print('=======content',str(price_data.content))
                price_data = price_data.json()['result']['list']
                prices = {x['symbol']: x['lastPrice'] for x in list(filter(lambda z: z['symbol'].rstrip('USDT') in coin_list,
                                                                           list(filter(lambda y: bool(y['symbol'].endswith('USDT')),
                                                                                       price_data))))}

                redis_conn.set(name="bybit_prices", value=json.dumps(prices))

            except Exception as e:
                print(e)
                raise e
        return