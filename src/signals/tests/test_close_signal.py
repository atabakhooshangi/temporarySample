from unittest import mock

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import StatusChoice, TradingSignalType
from core.test_utils import force_authenticator
from media.models import Media
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from user.models import Profile


class CloseSignalUnitTest(APITestCase):
    def setUp(self):
        profile = Profile.objects.create(
            owner_id=1,
            title='test_profile',
            username='test_profile',
            is_vendor=True,
        )
        coin = 'USDT'
        service = Service.objects.create(
            title='signal',
            link='http://test/test/service',
            description='for testing',
            profile=profile,
            coin=coin,
            subscription_fee=100,
        )

        exchange_market = ExchangeMarket.objects.create(
            exchange_name='test',
            coin_pair='BTCUSDT',
            coin_name='USDT/BTC',
            base_currency='SHIBA',
            quote_currency='USDT',
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.SPOT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the close signal that publish",
            image_id=Media.objects.get(key='test_key').id,
            virtual_value=100,
            pnl_amount=1,
            pnl_percentage=1
        )

        TradingSignal.objects.create(
            sid=service,
            type=TradingSignalType.SPOT,
            exchange_market=exchange_market,
            leverage=1000000,
            entry_point=50,
            percentage_of_fund=0.1,
            take_profit_1=200,
            stop_los=300,
            description="for test the close signal that start",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.START,
            virtual_value=100,
            pnl_amount=1,
            pnl_percentage=1
        )

    @force_authenticator
    def test_close_publish_signal(self):
        trading = TradingSignal.objects.get(description="for test the close signal that publish")
        url = reverse('signal-close', kwargs={'pk': trading.id})
        response = self.client.patch(url, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            trading.state,
            StatusChoice.CLOSE
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_close_publish_signal(self, mocked):
        trading = TradingSignal.objects.get(description="for test the close signal that start")
        url = reverse('signal-close', kwargs={'pk': trading.id})
        response = self.client.patch(url, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
