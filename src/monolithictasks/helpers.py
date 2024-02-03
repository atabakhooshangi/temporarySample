import requests


def get_irt_price():
    session = requests.Session()
    prices = session.get("https://api.wallex.ir/v1/trades?symbol=USDTTMN", timeout=13).json()
    irr_current_price = prices['result']['latestTrades'][0]['price']
    irt_price = irr_current_price.split('.')
    return irt_price[0]