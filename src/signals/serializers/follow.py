from rest_framework import serializers

from core.base_serializer import BaseModelSerializer
from signals.models.follow import UserFollowing, VendorFollower
from rest_framework.validators import UniqueTogetherValidator


class FollowingListSerializer(BaseModelSerializer):
    class Meta:
        model = UserFollowing
        fields = '__all__'

    def create(self, validated_data):
        VendorFollower.objects.create(vendor_id=validated_data.get('following').id,
                                      follower_id=validated_data.get('user').id
                                      )
        return super(FollowingListSerializer, self).create(validated_data)


class FollowingModelSerializer(serializers.Serializer):
    following_id = serializers.IntegerField()

    def create(self, validated_data):
        VendorFollower.objects.get_or_create(vendor_id=validated_data.get('following_id'),
                                             follower_id=validated_data.get('user_id')
                                             )
        obj, created = UserFollowing.objects.get_or_create(user_id=validated_data.get('user_id'),
                                                           following_id=validated_data.get('following_id'))
        return FollowingModelSerializer(obj).data
