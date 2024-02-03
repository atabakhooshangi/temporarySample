from unittest import mock

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import TradingSignalType
from core.test_utils import force_authenticator
from media.models.media import Media
from services.models import Service
from signals.models import TradingSignal, ExchangeMarket
from signals.models.comment import Comment
from user.models.profile import Profile


class CommentlUnitTest(APITestCase):

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
            description="for test comment on signal",
            image_id=Media.objects.get(key='test_key').id
        )

    def test_unauthorized_user(self):
        trading = TradingSignal.objects.get(description='for test comment on signal')
        url = reverse('comment', kwargs={'pk': trading.id})
        response = self.client.post(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    @mock.patch("core.api_gateways.ProducerClientGateway.produce", return_value=True)
    def test_create_comment(self, mocked):
        trading = TradingSignal.objects.get(description='for test comment on signal')
        url = reverse('comment', kwargs={'pk': trading.id})
        data = {
            "comment": "It's a first comment"
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
        self.assertEqual(
            response.data['comment'],
            "It's a first comment"
        )

    @force_authenticator
    def test_create_reply(self):
        trading = TradingSignal.objects.get(description='for test comment on signal')
        comment = Comment.objects.create(comment="for test te reply", trading_signal_id=trading.id,
                                         author_id=Profile.objects.first().id)
        url = reverse('reply-comment', kwargs={'pk': comment.id})
        data = {
            'comment': "reply on first comment"
        }
        response = self.client.post(url, data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
        self.assertEqual(
            response.data['parent_id'],
            comment.id
        )
