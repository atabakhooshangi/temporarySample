import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import ServiceTypeChoices, TradingSignalType
from core.test_utils import arbitrary_user_force_authenticator, force_authenticator
from media.models import Media
from services.models import Service
from signals.models import (
    ExchangeMarket,
    TradingSignal,
    VendorFollower,
    UserFollowing
)
from user.models import Profile, IAMUser


class ServiceListTest(APITestCase):
    def setUp(self) -> None:
        profile_1 = Profile.objects.create(
            owner_id=1,
            title='service_profile_1',
            username='service_profile_1',
            is_vendor=True,
        )
        profile_2 = Profile.objects.create(
            owner_id=2,
            title='service_profile_2',
            username='service_profile_2',
            is_vendor=True,
        )
        profile_3 = Profile.objects.create(
            owner_id=3,
            title='service_profile_3',
            username='service_profile_3',
            is_vendor=True,
        )
        service = Service.objects.create(
            title="test",
            description="test",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile_1,
            subscription_fee=1000,
            subscription_coin='usdt'
        )
        service = Service.objects.create(
            title="test",
            description="test",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile_2,
            subscription_fee=1000,
            subscription_coin='usdt'
        )
        UserFollowing.objects.create(
            user_id=profile_1.id,
            following_id=profile_2.id
        )

    @force_authenticator
    def test_list_my_service(self):
        url = reverse('service-me')
        response = self.client.get(url, format='json')
        self.assertEqual(
            len(response.data),
            1
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    # TODO: check the response data

    @force_authenticator
    def test_list_follow_service(self):
        url = reverse('service-follow')
        response = self.client.get(url, format='json')
        data = json.loads(response.content)[0]
        self.assertEqual(
            data.get('service_owner').get('id'),
            Profile.objects.get(title='service_profile_2').id
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )


class MyServiceListTest(APITestCase):
    def setUp(self) -> None:
        profile = Profile.objects.create(
            owner_id=1000,
            title='test_show_service_me',
            username='test_show_service_me',
            is_vendor=True,
        )
        service = Service.objects.create(
            title="test",
            description="test",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile,
            subscription_fee=1000,
            subscription_coin='usdt'
        )
        exchange_market = ExchangeMarket.objects.create(
            exchange_name="test",
            coin_pair='usdt/irr',
            coin_name='coin.name',
            base_currency='btc',
            quote_currency='usdt',
        )
        media = Media.objects.create(
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
            description="testing services me list",
            image_id=media.id
        )

    @arbitrary_user_force_authenticator(
        user=IAMUser(owner_id=1000, authentication_level="LEVEL_TWO", is_authenticated=True)
    )
    def test_list_service(self):
        url = reverse('service-me')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        json_response = response.json()
        self.assertIsInstance(json_response, list)
        self.assertEqual(len(json_response), 1)
        self.assertEqual(json_response[0]["title"], "test")
        self.assertEqual(json_response[0]["description"], "test")
        self.assertEqual(json_response[0]["subscription_fee"], 1000)
        self.assertEqual(json_response[0]["subscription_coin"], "usdt")


class FollowServiceListTest(APITestCase):
    def setUp(self) -> None:
        profile = Profile.objects.create(
            owner_id=1000,
            title='test_show_follow_service',
            username='vendor',
            is_vendor=True,
        )
        follower = Profile.objects.create(
            owner_id=1001,
            title='test_show_follow_service',
            username='follower',
            is_vendor=True,
        )
        VendorFollower.objects.create(
            vendor=profile,
            follower=follower
        )
        UserFollowing.objects.create(
            user=follower,
            following=profile
        )
        service = Service.objects.create(
            title="test",
            description="test",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile,
            subscription_fee=1000,
            subscription_coin='usdt'
        )
        exchange_market = ExchangeMarket.objects.create(
            exchange_name="test",
            coin_pair='usdt/irr',
            coin_name='coin.name',
            base_currency='btc',
            quote_currency='usdt',
        )
        media = Media.objects.create(
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
            image_id=media.id
        )

    @arbitrary_user_force_authenticator(
        user=IAMUser(owner_id=1001, authentication_level="LEVEL_TWO", is_authenticated=True)
    )
    def test_list_service(self):
        url = reverse('service-follow')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        json_response = response.json()
        # TODO complete
        # self.assertIsInstance(json_response, list)
        # self.assertEqual(len(json_response), 1)
        # self.assertEqual(json_response[0]["title"], "test")
        # self.assertEqual(json_response[0]["description"], "test")
        # self.assertEqual(json_response[0]["subscription_fee"], 1000)
        # self.assertEqual(json_response[0]["subscription_coin"], "usdt")
