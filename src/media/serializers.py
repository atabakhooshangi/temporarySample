from rest_framework import serializers

from core import choice_field_types
from media.models import Media


class UploadSerializer(
    serializers.Serializer
):
    content_type = serializers.ChoiceField(choices=choice_field_types.MediaType.choices)
    bucket = serializers.ChoiceField(choices=choice_field_types.BucketTypeChoices.choices, default='image')


class MediaModelSerializer(serializers.ModelSerializer):
    def __init__(self, use_cache=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._USE_CACHE = use_cache
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = Media
        fields = (
            'id',
            'key',
            'bucket',
            'media_url')
        read_only_fields = ('id',)

    def get_media_url(self, obj):
        if self._USE_CACHE:
            return obj.cached_external_media_url
        return obj.external_media_url
