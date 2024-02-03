from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.test_utils import force_authenticator, TEST_USER, arbitrary_user_force_authenticator
from media.models.media import Media
from user.models import IAMUser
from user.models.profile import Profile


class ProfileUpdateUnitTest(APITestCase):

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
            "image_id": Media.objects.get(key="test_key").id
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_update_profile(self):
        url = reverse('profile')
        data = {
            'username': "test_update_username",
            "title": "test_update_title",
            "description": "test_update_description",
            "image_id": Media.objects.get(key="test_key").id
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
            False
        )
        self.assertEqual(
            Profile.objects.get().description,
            "test_update_description"
        )

    @force_authenticator
    def test_update_profile_just_username(self):
        url = reverse('profile')
        profile = Profile.objects.get(owner_id=1)
        data = {
            'username': "test_update_username",
            "title": profile.title,
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        profile.refresh_from_db()
        self.assertEqual(
            profile.username,
            "test_update_username"
        )
        self.assertEqual(
            profile.description,
            "test_description"
        )
        self.assertEqual(
            profile.default_name,
            False
        )

    @force_authenticator
    def test_update_profile(self):
        url = reverse('profile')
        data = {
            'username': "test_update_username",
            "title": "test_update_title",
            "description": "test_update_description",
            "image_id": Media.objects.get(key="test_key").id
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
            False
        )
        self.assertEqual(
            Profile.objects.get().description,
            "test_update_description"
        )

    @force_authenticator
    def test_update_profile_with_invalid_data(self):
        url = reverse('profile')
        data = {"username": True}
        response = self.client.put(url, data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_profile_with_blank_value(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        data = {
            'username': "test_1",
            "title": "test_1",
        }
        response_1 = self.client.put(url, data, format='json')
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            Profile.objects.get(owner_id=2).default_name,
            False
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_username_profile_with_default_value(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        profile = Profile.objects.get(owner_id=2)
        data = {
            "username": "test_1",
            "title": profile.title,
        }
        response_1 = self.client.put(url, data, format='json')
        profile.refresh_from_db()
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            profile.default_name,
            True
        )
        self.assertEqual(
            profile.username,
            'test_1'
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_title_profile_with_default_value(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        profile = Profile.objects.get(owner_id=2)
        data = {
            'username': profile.username,
            "title": "test_1",
        }
        response_1 = self.client.put(url, data, format='json')
        profile.refresh_from_db()
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            profile.default_name,
            True
        )
        self.assertEqual(
            profile.title,
            'test_1'
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_profile(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        data = {
            'username': "test_1",
            "title": "test_1",
        }
        response_1 = self.client.put(url, data, format='json')
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            Profile.objects.get(owner_id=2).default_name,
            False
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_username_profile_with_default_value(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        profile = Profile.objects.get(owner_id=2)
        data = {
            "username": "test_1",
            "title": profile.title,
        }
        response_1 = self.client.put(url, data, format='json')
        profile.refresh_from_db()
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            profile.default_name,
            True
        )
        self.assertEqual(
            profile.username,
            'test_1'
        )

    @arbitrary_user_force_authenticator(user=IAMUser(owner_id=2, is_authenticated=True))
    def test_update_title_profile_with_default_value(self):
        data_1 = {
            'username': "",
            "title": "",
            "image_id": Media.objects.get(key="test_key").id
        }
        self.client.post(
            reverse('profile'),
            data_1,
            format='json'
        )
        url = reverse('profile')
        profile = Profile.objects.get(owner_id=2)
        data = {
            'username': profile.username,
            "title": "test_1",
        }
        response_1 = self.client.put(url, data, format='json')
        profile.refresh_from_db()
        self.assertEqual(
            response_1.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            profile.default_name,
            True
        )
        self.assertEqual(
            profile.title,
            'test_1'
        )
