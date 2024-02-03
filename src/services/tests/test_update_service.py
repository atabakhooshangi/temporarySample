from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import ServiceTypeChoices, ServiceStateChoices, ExchangeChoices
from core.test_utils import force_authenticator
from services.models import Service
from user.models import Profile


class ServiceUpdateTest(APITestCase):
    def setUp(self):
        service_owner_profile = Profile.objects.create(
            owner_id=1,
            title='test_update_service',
            username='test_update_service',
            is_vendor=True,
        )
        profile = Profile.objects.create(
            owner_id=2,
            title='test',
            username='test',
            is_vendor=True,
        )
        Service.objects.create(
            title="test_update_service_requested",
            description="test_update",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=service_owner_profile,
            state=ServiceStateChoices.REQUESTED,
        )
        Service.objects.create(
            title="test_update",
            description="test_update",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=service_owner_profile,
            subscription_fee=1000,
            state=ServiceStateChoices.TRACKING,
            exchanges=[ExchangeChoices.COINEX],
        )
        Service.objects.create(
            title="test_update_with_owner",
            description="test_update_with_owner",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=profile,
            subscription_fee=1000,
            state=ServiceStateChoices.TRACKING,
            exchanges=[ExchangeChoices.COINEX],
        )

    @force_authenticator
    def test_update_requested_service(self):
        service = Service.objects.get(
            title='test_update_service_requested'
        )
        url = reverse(
            'update-service',
            kwargs={'pk': service.id}
        )
        response = self.client.patch(
            url,
            data={
                "watch_list": ["BTC"],
                "subscription_fee":3000
            },
            format='json'
        )
        service.refresh_from_db()
        self.assertEqual(
            service.state,
            ServiceStateChoices.PENDING
        )
        self.assertEqual(
            service.subscription_fee,
            3000
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    def test_update_watch_list_and_exchanges(self):
        service = Service.objects.get(
            title='test_update'
        )
        self.assertEqual(
            service.watch_list,
            []
        )
        self.assertEqual(
            service.exchanges,
            ["COINEX"]
        )
        url = reverse(
            'update-service',
            kwargs=
            {
                'pk': service.id
            }
        )
        self.client.patch(url,
                          data={
                              "watch_list": ["BTC", "USDT"],
                              "exchanges": ["BYBIT", "WALLEX"]
                          },
                          format='json')
        service.refresh_from_db()
        self.assertEqual(
            service.state,
            ServiceStateChoices.TRACKING
        )
        self.assertEqual(
            service.exchanges,
            ["BYBIT", "WALLEX"]
        )
        self.assertEqual(
            service.watch_list,
            ["BTC", "USDT"]
        )

    @force_authenticator
    def test_pending_service_subscription_fee(self):
        service = Service.objects.get(
            title='test_update'
        )
        service.state = ServiceStateChoices.PENDING
        service.save()
        service.refresh_from_db()
        url = reverse(
            'update-service',
            kwargs=
            {
                'pk': service.id
            }
        )
        response = self.client.patch(
            url,
            data={
                "subscription_fee": 3000
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='en'
        )
        service.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(service.subscription_fee,
                         1000)

    @force_authenticator
    def test_publish_service_subscription_fee(self):
        service = Service.objects.get(
            title='test_update'
        )
        service.state = ServiceStateChoices.PUBLISH
        service.save()
        service.refresh_from_db()
        url = reverse(
            'update-service',
            kwargs=
            {
                'pk': service.id
            }
        )
        response = self.client.patch(
            url,
            data={
                "subscription_fee": 3000
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='en'
        )
        service.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(service.subscription_fee,
                         1000)


