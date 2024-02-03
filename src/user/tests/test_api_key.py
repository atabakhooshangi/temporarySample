from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from copytrading.models import ApiKey
from core.test_utils import TEST_USER, force_authenticator
from media.models import Media
from user.models import Profile


class ProfileUpdateUnitTest(APITestCase):

    def setUp(self) -> None:
        media = Media.objects.create(
            key="profile_img_key",
            bucket="profile_img_bucket"
        )
        user_1 = Profile.objects.create(
            owner_id=TEST_USER.owner_id,
            username="username_1",
            title="title",
            description="description",
            image_id=media.id,
        )
        user_2 = Profile.objects.create(
            owner_id=2,
            username="username_2",
            title="title",
            description="description",
            image_id=media.id,
        )
        ApiKey.objects.create(
            owner_id=user_1.id,
            name='api_key_user_1',
            exchange='CONEX',
            api_key='640c261fba02b40001f90491',
            secret_key='e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed'
        )
        ApiKey.objects.create(
            owner_id=user_2.id,
            name='api_key_1_user_2',
            exchange='CONEX',
            api_key='640c261fba02b40001f90492',
            secret_key='e3c57ac3-f9d2-4fe2-8252-35abbf41e4ed'
        )
        ApiKey.objects.create(
            owner_id=user_2.id,
            name='api_key_2_user_2',
            exchange='CONEX',
            api_key='640c261fba02v40001f90491',
            secret_key='e3c57ac3-r9d2-4fe2-8652-35abbf41e4ed'
        )

    def test_unauthorized(self):
        url = reverse('api-key-list')
        data = {
            "name": "test api key",
            "exchange": "COINEX",
            "api_key": "640c261fba02b40001f90491",
            "secret_key": "e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed"

        }
        response = self.client.post(
            url,
            data,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @force_authenticator
    def test_creat_api_key(self):
        url = reverse('api-key-list')
        data = {
            "name": "test api key",
            "exchange": "COINEX",
            "api_key": "640c261fba02b40001f90491",
            "secret_key": "e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed"

        }
        response = self.client.post(
            url,
            data,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    @force_authenticator
    def test_creat_api_key(self):
        url = reverse('api-key-list')
        data = {
            "name": "test api key",
            "exchange": "COINEX",
            "api_key": "640c261fba02b40001f90491",
            "secret_key": "e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed"

        }
        response = self.client.post(
            url,
            data,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    # @arbitrary_user_force_authenticator(
    #     user=IAMUser(
    #         owner_id=2,
    #         authentication_level="LEVEL_TWO",
    #         is_authenticated=True
    #     )
    # )
    @force_authenticator
    def test_list_user(self):
        response = self.client.get(
            reverse('api-key-list'),
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            len(response.data),
            1
        )

    @force_authenticator
    def test_retrieve_user(self):
        profile = Profile.objects.get(owner_id=TEST_USER.owner_id)
        url = reverse(
            'api-key-detail',
            kwargs=dict(pk=ApiKey.objects.get(owner_id=profile.id).pk)
        )
        response = self.client.get(
            url,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    @force_authenticator
    def test_update_user(self):
        profile = Profile.objects.get(owner_id=TEST_USER.owner_id)
        url = reverse(
            'api-key-detail',
            kwargs=dict(pk=ApiKey.objects.get(owner_id=profile.id).pk)
        )
        data = {
            "name": "test api key update",
            "exchange": "COINEX",
            "api_key": "640c261fba02b40001f90491",
            "secret_key": "e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed"

        }
        response = self.client.patch(
            url,
            data,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data['name'],
            data['name']
        )

    @force_authenticator
    def test_update_user(self):
        profile = Profile.objects.get(owner_id=TEST_USER.owner_id)
        url = reverse(
            'api-key-detail',
            kwargs=dict(pk=ApiKey.objects.get(owner_id=profile.id).pk)
        )
        data = {
            "name": "test api key update",
            "exchange": "COINEX",
            "api_key": "640c261fba02b40001f90491",
            "secret_key": "e3c57ac3-f9d2-4fe2-8652-35abbf41e4ed",
            "default": True

        }
        response = self.client.patch(
            url,
            data,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data['name'],
            data['name']
        )

    @force_authenticator
    def test_delete_user(self):
        profile = Profile.objects.get(owner_id=TEST_USER.owner_id)
        url = reverse(
            'api-key-detail',
            kwargs=dict(pk=ApiKey.objects.get(owner_id=profile.id).pk)
        )
        response = self.client.delete(
            url,
            format='json'
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT
        )
