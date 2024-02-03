from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.message_text import MessageText
from core.test_utils import force_authenticator
from signals.models.follow import UserFollowing, VendorFollower
from user.models import User, Profile


def get_or_create_user(email):
    obj, _created = User.objects.get_or_create(email=email)
    return obj


class TestFollow(APITestCase):

    def setUp(self) -> None:
        follower_user = User.objects.create(
            email='follower@gmail.com',
        )
        following_user_is_vendor = User.objects.create(
            email='following@gmail.com',
        )
        following_user_is_not_vendor = User.objects.create(
            email='NotVendor@gmail.com',
        )
        follower_user.set_password('123')
        following_user_is_vendor.set_password('123')
        following_user_is_not_vendor.set_password('123')
        follower_profile = Profile.objects.create(
            owner_id=follower_user.id,
            title='follower',
            username='follower'
        )
        Profile.objects.create(
            owner_id=following_user_is_vendor.id,
            title='following',
            username='following',
            is_vendor=True
        )
        Profile.objects.create(
            owner_id=following_user_is_not_vendor.id,
            title='not_vendor',
            username='not_vendor',
            is_vendor=False
        )

    @force_authenticator
    def test_follow(self):
        follower_profile = Profile.objects.get(username='follower')
        following_profile = Profile.objects.get(username='following')
        data = {'following_id': following_profile.id}
        response = self.client.post(reverse('follow'), data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
        profile_follower_result = UserFollowing.objects.filter(user_id=follower_profile.id,
                                                               following_id=following_profile.id)
        profile_following_result = VendorFollower.objects.filter(vendor_id=following_profile.id,
                                                                 follower_id=follower_profile.id)

        self.assertEqual(
            profile_following_result.count(),
            1
        )
        self.assertEqual(
            profile_follower_result.count(),
            1
        )

    @force_authenticator
    def test_follower_is_not_vendor(self):
        following_profile = Profile.objects.get(username='not_vendor')
        data = {'following_id': following_profile.id}
        response = self.client.post(reverse('follow'), data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_406_NOT_ACCEPTABLE
        )
        self.assertEqual(
            response.data.get('detail'),
            MessageText.UserISNotVendor406
        )

    @force_authenticator
    def test_follower_has_not_profile(self):
        data = {'following_id': 0}
        response = self.client.post(reverse('follow'), data=data, format='json')
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )
        self.assertEqual(
            response.data.get('detail'),
            MessageText.UserProfileIsNotFound404
        )
