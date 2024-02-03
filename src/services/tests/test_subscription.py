from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.choice_field_types import ServiceTypeChoices, ServiceStateChoices, SubscriptionPaymentTypeChoices
from core.test_utils import force_authenticator
from services.models import Service
from user.models import Profile


class SubscriptionTest(APITestCase):
    def setUp(self) -> None:
        service_owner_profile = Profile.objects.create(
            owner_id=2,
            title='test_subscribe',
            username='test_subscribe',
            is_vendor=True,
        )
        subscriber_profile = Profile.objects.create(
            owner_id=1,
            title='test_subscribe',
            username='test_subscribe',
            is_vendor=True,
        )
        Service.objects.create(
            title="test_service_subscribe_1",
            description="test_service_subscribe_1",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=service_owner_profile,
            state=ServiceStateChoices.PUBLISH,
            subscription_fee=100000,
            has_trial=True
        )
        Service.objects.create(
            title="test_service_subscribe_2",
            description="test_service_subscribe_2",
            service_type=ServiceTypeChoices.SIGNAL,
            profile=service_owner_profile,
            state=ServiceStateChoices.PUBLISH,
            subscription_fee=200000,
            has_trial=True
        )
        # TODO: test service is not publish
        # Service.objects.create(
        #     title="test_update",
        #     description="test_update",
        #     service_type=ServiceTypeChoices.SIGNAL,
        #     profile=service_owner_profile,
        #     subscription_fee=1000,
        #     state=ServiceStateChoices.TRACKING,
        #     exchanges=[ExchangeChoices.COINEX],
        # )
        # Service.objects.create(
        #     title="test_update_with_owner",
        #     description="test_update_with_owner",
        #     service_type=ServiceTypeChoices.SIGNAL,
        #     profile=profile,
        #     subscription_fee=1000,
        #     state=ServiceStateChoices.TRACKING,
        #     exchanges=[ExchangeChoices.COINEX],
        # )

    @force_authenticator

    def test_buy_trial_subscription(self):
        service = Service.objects.get(
            title='test_service_subscribe_1'
        )
        url = reverse(
            'service-subscribe',
            kwargs={'pk': service.id}
        )
        response = self.client.put(
            url,
            data={
                "client_redirect_url": 'https://exmartiz.com/social/',
                "payment_type": SubscriptionPaymentTypeChoices.TRIAL
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='en'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    def test_subscribe_service_more_than_once(self):
        service_1 = Service.objects.get(
            title='test_service_subscribe_1'
        )
        url = reverse(
            'service-subscribe',
            kwargs={'pk': service_1.id}
        )
        self.client.put(
            reverse(
                'service-subscribe',
                kwargs={'pk': service_1.id}),
            data={
                "client_redirect_url": 'https://exmartiz.com/social/',
                "payment_type": SubscriptionPaymentTypeChoices.TRIAL
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='en'
        )
        response = self.client.put(
            url,
            data={
                "client_redirect_url": 'https://exmartiz.com/social/',
                "payment_type": SubscriptionPaymentTypeChoices.TRIAL
            },
            format='json',
            HTTP_ACCEPT_LANGUAGE='en'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
