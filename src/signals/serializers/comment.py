from rest_framework import serializers

from core.base_serializer import BaseModelSerializer
from core.choice_field_types import MessageCategoryChoices
from core.systemic_message import send_systemic_message
from signals.models.comment import Comment
from user.serializers.profile import ProfileReadOnlySerializer


class CreateCommentModelSerializer(BaseModelSerializer):
    class Meta:
        model = Comment
        fields = (
            'id',
            'comment',
            'trading_signal_id'
        )
        extra_kwargs = {'trading_signal_id': {'required': False}}
        read_only_fields = ('id',)

    def create(self, validated_data):
        signal_owner_id = validated_data.pop("signal_owner_id")
        signal_coin_pair = validated_data.pop("signal_coin_pair")
        comment_author_title = validated_data.pop("comment_author_title")
        comment = super().create(validated_data)
        send_systemic_message(
            MessageCategoryChoices.SOCIAL_SIGNAL_COMMENT,
            signal_owner_id,
            dict(comment_author_title=comment_author_title, coin_pair=signal_coin_pair),
        )
        return comment


class ReplyCommentModelSerializer(BaseModelSerializer):
    class Meta:
        model = Comment
        fields = (
            'id',
            'comment',
            'parent_id'
        )
        read_only_fields = ('id',)


class CommentReadOnlySerializer(BaseModelSerializer):
    reply = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id',
            'trading_signal',
            'parent',
            'comment',
            'reply',
            'author',
            'created_at'
        )

    def get_reply(self, obj):
        serializer = CommentReadOnlySerializer(obj.children(), many=True)
        return serializer.data

    def get_author(self, obj):
        serializer = ProfileReadOnlySerializer(obj.author)
        return serializer.data
