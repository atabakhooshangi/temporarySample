from rest_framework.reverse import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from core.test_utils import force_authenticator, TEST_USER
from user.models.profile import Profile
from media.models.media import Media


class ProfileRetrieveUnitTest(APITestCase):

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
            instagram_id="test_instagram_id",
            telegram_id="test_telegram_id",
            twitter_id="test_twitter_id",
            youtube_id="test_youtube_id"
        )

    def test_unauthorized(self):
        url = reverse('profile')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_retrieve_profile(self):
        url = reverse('profile')
        response = self.client.get(url, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        json_response = response.json()
        self.assertEqual(
            Profile.objects.get().title,
            json_response["title"]
        )
        self.assertEqual(
            Profile.objects.get().username,
            json_response["username"]
        )
        # self.assertEqual(
        #     Profile.objects.get().image_id,
        #     json_response["image"]["id"]
        # )
        # self.assertEqual(
        #     Profile.objects.get().image.key,
        #     json_response["image"]["key"]
        # )
        # self.assertEqual(
        #     Profile.objects.get().image.bucket,
        #     json_response["image"]["bucket"]
        # )
        self.assertEqual(
            False,
            json_response["is_vendor"]
        )
        self.assertEqual(
            Profile.objects.get().description,
            json_response["description"]
        )
        self.assertEqual(
            Profile.objects.get().instagram_id,
            json_response["instagram_id"]
        )
        self.assertEqual(
            Profile.objects.get().telegram_id,
            json_response["telegram_id"]
        )
        self.assertEqual(
            Profile.objects.get().twitter_id,
            json_response["twitter_id"]
        )
        self.assertEqual(
            Profile.objects.get().youtube_id,
            json_response["youtube_id"]
        )
