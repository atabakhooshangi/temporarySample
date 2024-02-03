import requests
from typing import Union

from django_redis import get_redis_connection

from core.settings import ADDITIONAL_FEE_FOR_USDT_PRICE


def get_wallex_usdt_to_toman_price():
    with get_redis_connection(alias="data_cache") as redis_conn:
        wallex_usdt_price = redis_conn.get("wallex_usdt_price")
        if wallex_usdt_price:
            wallex_usdt_price = float(wallex_usdt_price)
            return wallex_usdt_price + (wallex_usdt_price * ADDITIONAL_FEE_FOR_USDT_PRICE / 100)
        prices = requests.get("https://api.wallex.ir/v1/trades?symbol=USDTTMN").json()
        irt_current_price = prices['result']['latestTrades'][0]['price']
        redis_conn.set(
            "wallex_usdt_price",
            f"{irt_current_price}",
            30
        )
        irt_current_price = float(irt_current_price)
        return irt_current_price + (irt_current_price * ADDITIONAL_FEE_FOR_USDT_PRICE / 100)


def calculate_draw_down(roi_values: list) -> Union[None, float]:
    """
    calculate the maximum draw down.
    the maximum loss from a peak to a 
    trough of a portfolio,before a new 
    peak is attained
    """
    if not roi_values:
        return
    max_value = max(roi_values)
    index = roi_values.index(max_value)
    new_roi_values = roi_values[index:]
    return abs(
        round(
            (max(new_roi_values) - min(new_roi_values)), 3
        )
    )


def calculate_maximum_draw_down(roi_values: list) -> Union[None, float]:
    draw_downs = []
    for i in range(len(roi_values), 0, -1):
        draw_downs.append(
            calculate_draw_down(roi_values[:i])
        )
    if not draw_downs:
        return

    return abs(
        round(
            max(draw_downs), 3
        )
    )


def calculate_initial_draw_down(roi_values: list):
    if not roi_values:
        return
    return abs(
        round(
            min(roi_values), 3
        )
    )
