from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import CoinChoices
from core.test_utils import force_authenticator
from media.models import Media
from services.models import Service
from signals.models import ExchangeMarket
from user.models import Profile


class UpdateSignalUnitTest(APITestCase):
    def setUp(self):
        profile = Profile.objects.create(
            owner_id=1,
            title='test_profile',
            username='test_profile',
            is_vendor=True,
        )
        Service.objects.create(
            title='signal_1',
            link='http://test/test/service_1',
            description='for testing',
            profile=profile,
            coin=CoinChoices.USDT,
            subscription_fee=100,
        )
        Service.objects.create(
            title='signal_2',
            link='http://test/test/service_2',
            description='for testing',
            profile=profile,
            coin=CoinChoices.IRR,
            subscription_fee=100,
        )
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        ExchangeMarket.objects.create(
            exchange_name='test',
            coin_pair='USDT/IRR',
            coin_name='USDT/IRR',
            base_currency='btc',
            quote_currency='usdt',
        )
        ExchangeMarket.objects.create(
            exchange_name='test',
            coin_pair='BTC/IRR',
            coin_name='BTC/IRR',
            base_currency='btc',
            quote_currency='usdt',
        )

    def test_list_exchange_market_without_authenticate(self):
        url = reverse('exchange-market')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_list_exchange_market_with_authenticate(self):
        url = reverse('exchange-market', kwargs=dict(pk=Service.objects.get(title="signal_2").pk))
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        # FIXME: this assertion does not work and needs a patch
        # self.assertEqual(
        #     len(response.data),
        #     ExchangeMarket.objects.all().count()
        # )
