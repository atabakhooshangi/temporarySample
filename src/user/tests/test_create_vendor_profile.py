from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.test_utils import TEST_USER, arbitrary_user_force_authenticator
from media.models.media import Media
from user.models import Profile, IAMUser


class VendorProfileCreateUnitTest(APITestCase):

    def setUp(self) -> None:
        media = Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )
        Profile.objects.create(
            owner_id=TEST_USER.owner_id,
            username="test_username",
            title="test_title",
            description="test_description",
            image_id=media.id,
        )

    def test_unauthorized(self):
        url = reverse('profile')
        data = {
            'username': "test_update_username",
            "title": "test_update_title",
            "description": "test_update_description",
            "image_id": Media.objects.get(key="test_key").id,
            "instagram_id": "test_instagram_id",
            "telegram_id": "test_telegram_id",
            "twitter_id": "test_twitter_id",
            "youtube_id": "test_youtube_id",
            "analytics": dict(test_key="test_value"),
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @arbitrary_user_force_authenticator(
        user=IAMUser(
            owner_id=1,
            authentication_level="LEVEL_TWO",
            is_authenticated=True)
    )
    def test_vendor_profile_create(self):
        url = reverse('profile-vendor')
        data = {
            'username': "test_update_username",
            "title": "test_update_title",
            "description": "test_update_description",
            "image_id": Media.objects.get(key="test_key").id,
            "instagram_id": "test_instagram_id",
            "telegram_id": "test_telegram_id",
            "twitter_id": "test_twitter_id",
            "youtube_id": "test_youtube_id",
            "analytics": dict(test_key="test_value"),
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            Profile.objects.count(),
            1
        )
        self.assertEqual(
            Profile.objects.get().username,
            "test_update_username"
        )
        self.assertEqual(
            Profile.objects.get().title,
            "test_update_title"
        )
        self.assertEqual(
            Profile.objects.get().image_id,
            Media.objects.get(key="test_key").id
        )
        self.assertEqual(
            Profile.objects.get().is_vendor,
            True
        )
        self.assertEqual(
            Profile.objects.get().description,
            "test_update_description"
        )

    @arbitrary_user_force_authenticator(
        user=IAMUser(
            owner_id=1,
            authentication_level="LEVEL_TWO",
            is_authenticated=True
        )
    )
    def test_create_vendor_profile_with_invalid_data(self):
        url = reverse('profile')
        data = {"username": True}
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )
