from datetime import date

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import TradingSignalType, PositionChoice, StatusChoice, ServiceStateChoices
from core.test_utils import force_authenticator
from media.models import Media
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from user.models import Profile


class UpdateSignalUnitTest(APITestCase):
    def setUp(self):
        profile = Profile.objects.create(
            owner_id=1,
            title='test_profile',
            username='test_profile',
            is_vendor=True,
        )
        service_1 = Service.objects.create(
            title='signal_1',
            link='http://exwino/test/service_1',
            description='for testing',
            profile=profile,
            coin='USDT',
            subscription_fee=100,
            state=ServiceStateChoices.PUBLISH
        )
        service_2 = Service.objects.create(
            title='signal_2',
            link='http://exwino/test/service_2',
            description='for testing',
            profile=profile,
            coin='USDT',
            subscription_fee=100,
            state=ServiceStateChoices.PUBLISH
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        exchange_market = ExchangeMarket.objects.create(
            exchange_name='exwino',
            coin_pair='BTCUSDT',
            coin_name='USDT/BTC',
            base_currency='BTC',
            quote_currency='USDT',
        )
        TradingSignal.objects.create(
            sid=service_1,
            type=TradingSignalType.SPOT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the show",
            image_id=Media.objects.get(key='test_key').id
        )
        TradingSignal.objects.create(
            sid=service_1,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the show",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.CLOSE,
            closed_datetime=date.today(),
            stop_los_hit_datetime=date.today()
        )
        TradingSignal.objects.create(
            sid=service_2,
            type=TradingSignalType.FUTURES,
            position=PositionChoice.SHORT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the show",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.CLOSE,
            closed_datetime=date.today(),
            stop_los_hit_datetime=date.today()
        )

    @force_authenticator
    def test_show_signal(self):
        url = reverse('all-signal')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data['count'],
            TradingSignal.objects.all().count()
        )

    # def test_show_signal(self): TODO: Active when handle permission problem
    #     url = reverse('all-signal')
    #     response = self.client.get(url, format='json')
    #     self.assertEqual(
    #         response.status_code,
    #         status.HTTP_200_OK
    #     )
    #     self.assertEqual(
    #         response.data
    #     )
