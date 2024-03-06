import math

from datetime import datetime

from django.test import TestCase

from core.choice_field_types import TradingSignalType, StatusChoice, PositionChoice
from media.models import Media
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from signals.pnl import SignalPnLCalculator
from user.models.profile import Profile


class PnLCalculationUnitTest(TestCase):
    def setUp(self) -> None:
        profile = Profile.objects.create(
            owner_id=1,
            title='test_profile',
            username='test_profile',
            is_vendor=True,
        )
        service = Service.objects.create(
            title='signal',
            link='http://test/test/service',
            description='for testing',
            profile=profile,
            coin="USDT",
            subscription_fee=100,
        )

        exchange_market = ExchangeMarket.objects.create(
            exchange_name='test',
            coin_pair='USDT',
            coin_name='USDT',
            base_currency='BTC',
            quote_currency='USDT',
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.LONG,
            exchange_market=exchange_market,
            leverage=10,
            entry_point=19500,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=10,
            take_profit_1=20000,
            take_profit_1_hit_datetime=datetime.now(),
            take_profit_2=22000,
            stop_los=18000,
            stop_los_hit_datetime=datetime.now(),
            description="for test the close signal that start",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.CLOSE,
            volume=30,
            virtual_value=100,
        )

        TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=20,
            entry_point=19500,
            entry_point_hit_datetime=datetime.now(),
            percentage_of_fund=10,
            take_profit_1=18500,
            take_profit_1_hit_datetime=datetime.now(),
            take_profit_2=17000,
            stop_los=20000,
            stop_los_hit_datetime=datetime.now(),
            description="for test the close signal that start",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.CLOSE,
            volume=30,
            virtual_value=100,
        )
        return super().setUp()

    def test_signal_pnl(self):
        long_signal = TradingSignal.objects.get(
            type=TradingSignalType.FUTURES,
            position=PositionChoice.LONG,
        )
        short_signal = TradingSignal.objects.get(
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
        )
        long_signal_pnl = SignalPnLCalculator(
            long_signal,
            quote_currency=long_signal.exchange_market.quote_currency,
            base_currency=long_signal.exchange_market.base_currency,
        ).pnl_calculator()["pnl_amount"]

        assert math.ceil(long_signal_pnl * 100) / 100.0 == -46.15
        short_signal_pnl = SignalPnLCalculator(
            short_signal,
            quote_currency=long_signal.exchange_market.quote_currency,
            base_currency=long_signal.exchange_market.base_currency
        ).pnl_calculator()["pnl_percentage"]
        assert math.ceil(short_signal_pnl * 100) / 100.0 == -5.12
