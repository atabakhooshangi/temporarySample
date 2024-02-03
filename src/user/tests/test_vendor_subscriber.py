from datetime import datetime, timedelta

from rest_framework.reverse import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from core.choice_field_types import ServiceTypeChoices, ServiceStateChoices, SubscriptionPaymentTypeChoices
from core.test_utils import force_authenticator, TEST_USER, arbitrary_user_force_authenticator
from services.models import Subscription, Service
from user.models import IAMUser
from user.models.profile import Profile
from media.models.media import Media


class VendorSubscriber(APITestCase):

    def setUp(self) -> None:
        media = Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        vendor = Profile.objects.create(
            owner_id=TEST_USER.owner_id,
            username="test_username_vendor",
            title="test_title_vendor",
            description="test_description",
            image_id=media.id,
            is_vendor=True
        )
        profile_1 = Profile.objects.create(
            owner_id=2,
            username="test_username",
            title="test_title",
            description="test_description",
            image_id=media.id,
        )
        profile_2 = Profile.objects.create(
            owner_id=3,
            username="test_username",
            title="test_title",
            description="test_description",
            image_id=media.id,
        )
        service = Service.objects.create(
            profile=vendor,
            service_type=ServiceTypeChoices.SIGNAL,
            subscription_fee=10,
            subscription_coin='USDT',
            state=ServiceStateChoices.PUBLISH,
            has_trial=True,
        )
        Subscription.objects.create(
            service=service,
            payment_type=SubscriptionPaymentTypeChoices.TRIAL,
            subscriber=profile_2,
            amount=0,
            start_time=datetime.now(),
            expire_time=datetime.now() + timedelta(days=10),
            is_paid=True
        )
        Subscription.objects.create(
            service=service,
            payment_type=SubscriptionPaymentTypeChoices.IRT_PAID,
            subscriber=profile_2,
            amount=10,
            start_time=datetime.now(),
            expire_time=datetime.now() + timedelta(days=10),
            is_paid=True
        )
        Subscription.objects.create(
            service=service,
            payment_type=SubscriptionPaymentTypeChoices.IRT_PAID,
            subscriber=profile_2,
            amount=10,
            start_time=datetime.now() - timedelta(days=10),
            expire_time=datetime.now() - timedelta(days=2),
            is_paid=True
        )

    def test_unauthorized(self):
        url = reverse('vendor-subscriber')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_subscriber_permission_is_vendor(self):
        url = reverse('vendor-subscriber')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @arbitrary_user_force_authenticator(
        user=IAMUser(
            owner_id=2,
            authentication_level="LEVEL_TWO",
            is_authenticated=True
        )
    )
    def test_subscriber_permission_is_not_vendor(self):
        url = reverse('vendor-subscriber')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    @force_authenticator
    def test_vendor_subscriber(self):
        url = reverse('vendor-subscriber')
        response = self.client.get(url)
        result_count = len(response.json().get('results'))
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            result_count,
            1
        )
