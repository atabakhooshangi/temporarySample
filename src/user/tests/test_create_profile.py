from rest_framework.reverse import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from core.test_utils import force_authenticator
from user.models.profile import Profile
from media.models.media import Media


class ProfileCreateUnitTest(APITestCase):

    def setUp(self) -> None:
        Media.objects.create(
            key="test_key",
            bucket="test_bucket"
        )

    def test_unauthorized(self):
        url = reverse('profile')
        data = {
            'username': "test_username",
            "title": "test_title",
            "image_id": Media.objects.get(key="test_key").id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_create_profile(self):
        url = reverse('profile')
        data = {
            'username': "test_username",
            "title": "test_title",
            "image_id": Media.objects.get(key="test_key").id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
        self.assertEqual(
            Profile.objects.count(),
            1
        )
        self.assertEqual(
            Profile.objects.get().username,
            "test_username"
        )
        self.assertEqual(
            Profile.objects.get().title,
            "test_title"
        )
        self.assertEqual(
            Profile.objects.get().image_id,
            Media.objects.get(key="test_key").id
        )
        self.assertEqual(
            Profile.objects.get().is_vendor,
            False
        )

    @force_authenticator
    def test_create_profile_with_incomplete_data(self):
        url = reverse('profile')
        data = {
            "title": "test_title",
            "image_id": Media.objects.get(key="test_key").id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    def test_create_profile_with_invalid_data(self):
        url = reverse('profile')
        data = {"username": True}
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @force_authenticator
    def test_create_profile_with_blank_value(self):
        url = reverse('profile')
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        data_2 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        response_1 = self.client.post(url, data_1, format='json')
        self.assertEqual(
            response_1.status_code,
            status.HTTP_201_CREATED
        )

