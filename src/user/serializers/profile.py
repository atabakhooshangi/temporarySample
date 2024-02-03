import random
import re
import time
from random import Random

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from copytrading.models import ApiKey
from core.message_text import MessageText
from core.choice_field_types import CoinChoices, ServiceTypeChoices, SubscriptionPaymentTypeChoices
from core.utils import base36encode
from media.models import Media
from media.serializers import MediaModelSerializer
from services.models import Service, Subscription
from user.exceptions import UserProfileIsExists, ApiKeyExist
from user.models import Profile, VendorProfileAnalytic


class UsernameAndTitleValidatorMixin:
    def _validate_length(self, value):
        if not (4 <= len(value) <= 20):
            raise serializers.ValidationError(
                MessageText.InvalidLength400
            )
        return

    def _validate_characters(self, value):
        valid_character_pattern = re.compile(r'^[0-9a-zA-Z_.]*$')
        if not re.match(valid_character_pattern, value):
            raise serializers.ValidationError(
                MessageText.UnacceptableCharacters400
            )

    def _validate_unique(self, value, field):
        if Profile.objects.filter(**{field: value}).exists():
            raise serializers.ValidationError(
                MessageText.UniqueConstraint400
            )

    def validate_username(self, value):
        self._validate_length(value)
        self._validate_characters(value)
        self._validate_unique(value, field="username__iexact")
        return value

    def validate_title(self, value):
        self._validate_length(value)
        self._validate_characters(value)
        self._validate_unique(value, field="title__iexact")
        return value


class ProfileCreateSerializer(
    serializers.Serializer,
    UsernameAndTitleValidatorMixin
):
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(),
        required=False,
        allow_null=True
    )
    title = serializers.CharField(
        required=False,
        allow_blank=True
    )
    username = serializers.CharField(
        required=True,
        allow_null=False,
        allow_blank=True,
        validators=[
            UniqueValidator(
                queryset=Profile.objects.all()
            )
        ]
    )
    default_name = serializers.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = (
            "title",
            "username",
            "image_id",
            'default_name'
        )

    def to_internal_value(self, data):
        if not Profile.objects.filter(owner_id=data.get('owner_id')):
            timestamp = int(time.time() * 10000000)
            rand_num = random.randint(9999, 99999)
            obj = base36encode(int(str(timestamp) + str(rand_num)))

            if data.get('username', None) == '':
                data['username'] = obj
                data['default_name'] = True
            if data.get('title', None) == '':
                data['title'] = obj
                data['default_name'] = True
        return super(ProfileCreateSerializer, self).to_internal_value(data=data)

    @atomic
    def create(self, validated_data):
        if not Profile.objects.filter(owner_id=validated_data.get('owner_id')):
            image_id = validated_data.pop("image_id", None)
            profile = Profile.objects.create(
                # owner_id passed in perform_create method
                **validated_data
            )
            profile.image_id = image_id
            profile.save()
        else:
            raise UserProfileIsExists
        return profile


class ProfileModelSerializer(
    serializers.ModelSerializer,
    UsernameAndTitleValidatorMixin
):
    image = MediaModelSerializer(read_only=True)
    subscribed_signal_service_count = serializers.IntegerField(read_only=True)
    following_number = serializers.IntegerField(read_only=True)
    used_trial_num = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "title",
            "username",
            "description",
            "image_id",
            "is_vendor",
            "is_signal_vendor",
            "is_copy_vendor",
            "instagram_id",
            "youtube_id",
            "telegram_id",
            "twitter_id",
            "trading_view_id",
            "state",
            "image",
            "default_name",
            "subscribed_signal_service_count",
            "following_number",
            "used_trial_num",
            "quick_signal"
        )
        read_only_fields = (
            "state",
            "is_vendor",
            "trading_view_id",
            "state",
            "used_trial_num",
            "quick_signal"
        )
        extra_kwargs = {
            'image_id': {
                'write_only': True,
                'required': False,
                'allow_null': True,
                'source': 'image'
            },
            'title': {'required': False},
            'username': {'required': False},
            "instagram_id": {'required': False},
            "youtube_id": {'required': False},
            "telegram_id": {'required': False},
            "twitter_id": {'required': False},

        }

    def get_used_trial_num(self, obj):
        if not self.context['request'].user.is_authenticated:
            return None
        count = Subscription.objects.filter(
            payment_type=SubscriptionPaymentTypeChoices.TRIAL,
            subscriber__owner_id=self.context['request'].user.owner_id
        ).count()
        return count

    def to_internal_value(self, data):
        username = data.get('username', None)
        title = data.get('title', None)
        if username != "" and \
                title != "" and self.instance.default_name:
            if username != self.instance.username and \
                    title != self.instance.title:
                data['default_name'] = False
            if username == self.instance.username:
                data.pop('username')
            if title == self.instance.title:
                data.pop('title')
        elif data.get('username', None) == '':
            data['username'] = self.instance.username
        elif data.get('title', None) == '':
            data['title'] = self.instance.title
        elif username != "" and \
                title != "" and \
                not self.instance.default_name and \
                (username == self.instance.username or \
                 title == self.instance.title):
            if username == self.instance.username:
                data.pop('username')
            if title == self.instance.title:
                data.pop('title')
        return super(ProfileModelSerializer, self).to_internal_value(data=data)

    def update(self, profile, validated_data):
        title = validated_data.get("title")
        if title:
            profile.services.all().update(title=title)

        return super().update(profile, validated_data)


class ProfileReadOnlySerializer(serializers.ModelSerializer):
    image = MediaModelSerializer(read_only=True, use_cache=True)
    service_id = serializers.IntegerField(required=False)

    class Meta:
        model = Profile
        fields = (
            'id',
            'service_id',
            'title',
            'username',
            'image',

        )


class ProfileMinimalReadOnlySerializer(serializers.ModelSerializer):
    image = MediaModelSerializer()

    class Meta:
        model = Profile
        fields = (
            'id',
            'owner_id',
            "image",
            'title',
            'username',
            'state',
            'is_vendor'
        )


class VendorProfileModelSerializer(serializers.ModelSerializer):
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(),
        required=False,
        allow_null=True
    )
    service_type = serializers.ChoiceField(
        choices=ServiceTypeChoices.choices,
        write_only=True,
        required=False,
        allow_null=True
    )
    analytics = serializers.JSONField(
        required=False,
        allow_null=True
    )
    coin = serializers.ChoiceField(
        choices=CoinChoices.choices,
        required=False,
        allow_null=True
    )
    subscription_coin = serializers.ChoiceField(
        choices=CoinChoices.choices,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Profile
        read_only_fields = (
            'image',
            'is_vendor',
            'state'
        )
        fields = (
            "title",
            "username",
            "description",
            "image_id",
            "state",
            "instagram_id",
            "youtube_id",
            "telegram_id",
            "twitter_id",
            "trading_view_id",
            "analytics",
            "subscription_coin",
            "coin",
            "service_type"
        )

    @atomic
    def update(self, profile: Profile, validated_data):
        subscription_coin = validated_data.pop("subscription_coin", None)
        coin = validated_data.pop("coin", None)
        service_type = validated_data.pop(
            "service_type",
            ServiceTypeChoices.SIGNAL
        )
        image_id = validated_data.pop("image_id", None)
        profile: Profile = super().update(profile, validated_data)
        if not VendorProfileAnalytic.objects.filter(
                profile=profile
        ).exists():
            VendorProfileAnalytic.objects.create(
                profile=profile,
                analytics=validated_data.get("analytics", dict())
            )

        if not Service.objects.filter(
                profile=profile,
                service_type=service_type
        ).exists():
            Service.objects.create(
                profile=profile,
                service_type=service_type,
                title=profile.title,
                coin=coin or CoinChoices.USDT,
                subscription_coin=subscription_coin or CoinChoices.USDT,
            )
        profile.is_vendor = True
        profile.image_id = image_id
        profile.save()

        return profile


class CopyApiSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ApiKey
        fields = (
            'id',
            'created_at',
            'owner',
            'name',
            'exchange',
            'api_key',
            'secret_key',
            'is_default'
        )
        extra_kwargs = {
            "secret_key": {'required': False, 'allow_null': True},
        }

    def to_internal_value(self, data):
        data['owner'] = Profile.objects.get(
            owner_id=self.context['request'].user.owner_id
        ).id
        try:
            secret_key_filter = Q(secret_key=data.get('secret_key')) if 'secret_key' in data else Q(
                secret_key__isnull=True)
            ApiKey.objects.get(secret_key_filter,
                               api_key=data.get('api_key'),
                               exchange=data.get('exchange')
                               )
            raise ApiKeyExist
        except ApiKey.DoesNotExist:
            return super(CopyApiSerializer, self).to_internal_value(data)


class CopyApiEditSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ApiKey
        fields = (
            'name',
            'is_default',
            'id',
            'owner',
            'exchange',
            'api_key',
            'secret_key',
            'is_default'
        )
        read_only_fields = (
            'id',
            'owner',
            'exchange',
            'api_key',
            'secret_key'
        )
