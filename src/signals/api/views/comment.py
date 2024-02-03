from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from signals.exceptions import TradingSignalIsNotFound
from signals.models.comment import Comment
from signals.models.signal import TradingSignal
from signals.serializers.comment import (
    CreateCommentModelSerializer,
    ReplyCommentModelSerializer,
    CommentReadOnlySerializer,
)
from user.exceptions import UserProfileNotFound
from user.models import Profile


class CommentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet
):

    def get_queryset(self):
        if self.action == 'list':
            return Comment.objects.filter(is_deleted=False, trading_signal_id=self.kwargs.get('pk'))
        return Comment.objects.filter(is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'list':
            return CommentReadOnlySerializer
        if self.action == 'create':
            return CreateCommentModelSerializer
        return ReplyCommentModelSerializer

    def perform_create(self, serializer):
        try:
            trading_signal_obj = TradingSignal.objects.select_related("exchange_market")\
                                                      .get(id=self.kwargs.get('pk'))
            author: Profile = Profile.objects.get(owner_id=self.request.user.owner_id)
        except TradingSignal.DoesNotExist:
            raise TradingSignalIsNotFound
        except Exception as e:
            raise UserProfileNotFound
        return serializer.save(
            trading_signal_id=trading_signal_obj.id,
            author_id=author.id,
            comment_author_title=author.title,
            signal_coin_pair=trading_signal_obj.exchange_market.coin_name,
            signal_owner_id=trading_signal_obj.sid.profile.owner_id
        )

    @action(
        methods=["POST"],
        detail=True,
        url_path="reply"
    )
    def reply(self, request, *args, **kwargs):
        try:
            author_id = self.request.user.owner_id
        except:
            raise UserProfileNotFound
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(parent_id=self.get_object().id, author_id=Profile.objects.get(owner_id=author_id).id)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
