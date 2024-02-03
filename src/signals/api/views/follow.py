from django.core.cache import cache
from django.db import models
from django_redis import get_redis_connection
from rest_framework import mixins
from rest_framework import response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet

from core.choice_field_types import ServiceTypeChoices
from services.models import Service
from signals.exceptions import UserISNotVendor, UserProfileIsNotFound
from signals.models.follow import UserFollowing, VendorFollower
from signals.serializers.follow import FollowingModelSerializer
from user.models import Profile
from user.serializers.profile import ProfileReadOnlySerializer


class FollowViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet
):
    queryset = UserFollowing.objects.all()

    def get_serializer_class(self):
        if self.action in ['follower', 'following']:
            return ProfileReadOnlySerializer
        return FollowingModelSerializer

    def perform_create(self, serializer):
        try:
            if not Profile.objects.get(id=self.request.data.get('following_id')).is_vendor:
                raise UserISNotVendor
            profile = Profile.objects.get(owner_id=self.request.user.owner_id)
        except Profile.DoesNotExist as e:
            raise UserProfileIsNotFound
        return serializer.save(user_id=profile.id)

    def destroy(self, request, *args, **kwargs):
        following_id = kwargs["pk"]
        owner_id = self.request.user.owner_id
        VendorFollower.objects.filter(
            vendor_id=following_id, follower__owner_id=owner_id
        ).delete()
        user = Profile.objects.get(owner_id=owner_id)
        following = Profile.objects.get(id=following_id)
        user.following_num -= 1
        following.follower_num -= 1
        user.save()
        following.save()
        UserFollowing.objects.filter(
            user__owner_id=owner_id, following_id=following_id
        ).delete()
        return response.Response(status=HTTP_204_NO_CONTENT)

    @action(methods=['GET'],
            detail=True,
            url_name='follower',
            url_path='follower'
            )
    def follower(self, request, *args, **kwargs):
        follower = VendorFollower.objects.filter(vendor_id=self.kwargs.get('pk')).values_list('follower_id', flat=True)
        serializer = self.get_serializer(Profile.objects.filter(id__in=follower), many=True)
        return response.Response(serializer.data)

    @action(methods=['GET'],
            detail=True,
            url_name='following',
            url_path='following'
            )
    def following(self, request, *args, **kwargs):
        following = UserFollowing.objects.filter(user_id=self.kwargs.get('pk')).values_list('following_id',
                                                                                            flat=True)
        serializer = self.get_serializer(
            Profile.objects.filter(id__in=following).annotate(
                service_id=models.Subquery(
                    Service.objects.filter(
                        profile_id=models.OuterRef('id'),
                        service_type=ServiceTypeChoices.SIGNAL
                    )[:1].values('id')

                )
            ),
            many=True
        )
        return response.Response(serializer.data)
