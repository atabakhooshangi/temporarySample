import pytest

from media.models import Media
from services.models import Coin, Service
from signals.models import Market, Exchange, ExchangeMarket, TradingSignal
from user.models import Profile


@pytest.fixture
def create_profile(db):
    profile = Profile.objects.create(
        owner_id=1,
        title='test_profile',
        username='test_profile',
        is_vendor=True,
    )
    return profile


@pytest.fixture
def create_coin(db):
    coin = Coin.objects.create(
        name='usdt'
    )
    return coin


@pytest.fixture
def create_service(db):
    service = Service.objects.create(
        title='signal',
        link='http://test/service',
        description='for testing',
        profile=create_profile(),
        coin=create_coin(),
        subscription_fee=100,
    )
    return service


@pytest.fixture
def create_exchange_market(db):
    exchange_market = ExchangeMarket.objects.create(
        exchange_name='test',
        coin_pair='usdt',
        coin_name='irr',
        base_currency='btc',
        quote_currency='usdt',
    )
    return exchange_market


@pytest.fixture
def create_Signal(db):
    trading_signal = TradingSignal.objects.create(
        sid=Service.objects.get(link='http://test/test/service'),
        type="spot",
        market_id=Market.objects.get(primary_coin='irr', secoundary_coin='usdt'),
        exchange_market=create_exchange_market(),
        leverage=1000000,
        entry_point=50,
        percentage_of_fund=0.1,
        take_profit_1=200,
        stop_los=300,
        description="for test the update signal",
        image_id=Media.objects.get(key='test_key').id
    )
    return trading_signal
