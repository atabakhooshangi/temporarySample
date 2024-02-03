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
        service = Service.objects.create(
            title='signal',
            link='http://exwino/test/service',
            description='for testing',
            profile=profile,
            coin='USDT',
            subscription_fee=100,
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        exchange_market = ExchangeMarket.objects.create(
            exchange_name='exwino',
            coin_pair='USDT',
            coin_name='USDT',
            base_currency='btc',
            quote_currency='usdt',
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
            description="for test the delete signal that published",
            image_id=Media.objects.get(key='test_key').id,
            virtual_value=100
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
            description="for test the close signal that draft",
            image_id=Media.objects.get(key='test_key').id,
            state=StatusChoice.DRAFT,
            virtual_value=100
        )

    @force_authenticator
    def test_delete_draft_signal(self):
        trading = TradingSignal.objects.get(description="for test the close signal that draft")
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.delete(url, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )
        self.assertEqual(
            trading.is_deleted,
            True
        )

    @force_authenticator
    def test_delete_published_signal(self):
        trading = TradingSignal.objects.get(description="for test the delete signal that published")
        url = reverse('signal-detail', kwargs={'pk': trading.id})
        response = self.client.delete(url, format='json')
        trading.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )
        self.assertEqual(
            trading.is_deleted,
            True
        )
