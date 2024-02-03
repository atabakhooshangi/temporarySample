import json
from datetime import datetime, timedelta, date

from django.db import models
from django.db.models import Q, OuterRef, Window, F, Value, Subquery
from django.db.models.functions import Coalesce
from django.db.models.functions import Rank
from django_redis import get_redis_connection
from rest_framework import serializers

from core.base_serializer import BaseModelSerializer
from core.choice_field_types import (
    ServiceStateChoices,
    StatusChoice, HistoryTypeChoices
)
from core.choice_field_types import SubscriptionPaymentTypeChoices
from core.date_utils import previous_week_range
from core.settings import (
    MAX_DIGIT,
    DECIMAL_PLACE
)
from core.sql_functions import SubquerySum, SubqueryCount
from media.models import Media
from services.cache_utils import cache_roi_and_draw_down
from services.models import (
    Service,
    DailyAggregatedPnl,
    Subscription, DailyROI
)
from signals.models import TradingSignal
from signals.pnl import risk_evaluation
from user.models import Profile
from user.serializers.profile import ProfileReadOnlySerializer


class BaseServiceReadOnlySerializer(BaseModelSerializer):
    service_owner = ProfileReadOnlySerializer(source="profile")
    signal_count = serializers.IntegerField()
    follower_number = serializers.IntegerField()
    following_number = serializers.IntegerField()
    instagram_id = serializers.CharField(source="profile.instagram_id")
    youtube_id = serializers.CharField(source="profile.youtube_id")
    telegram_id = serializers.CharField(source="profile.telegram_id")
    twitter_id = serializers.CharField(source="profile.twitter_id")
    overall_roi = serializers.SerializerMethodField()
    used_trial = serializers.SerializerMethodField(read_only=True)
    virtual_value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Service
        fields = (
            'id',
            'title',
            'service_owner',
            'description',
            'state',
            'service_type',
            'subscription_fee',
            'subscription_coin',
            'has_trial',
            'overall_roi',
            'follower_number',
            'following_number',
            'instagram_id',
            'youtube_id',
            'telegram_id',
            'twitter_id',
            'used_trial',
            'virtual_value'
        )

    def get_overall_roi(self, obj):
        with get_redis_connection(alias="data_cache") as redis_conn:
            cached_data = redis_conn.get(f"OVERALL_ROI:service_id:{obj.id}")
            if cached_data:
                return json.loads(cached_data)
            return cache_roi_and_draw_down(service=obj, expire_in=60 * 60, history_type=HistoryTypeChoices.OVERALLY)

    def get_used_trial(self, obj):
        if not self.context['request'].user.is_authenticated:
            return None
        count = Subscription.objects.filter(
            payment_type=SubscriptionPaymentTypeChoices.TRIAL,
            subscriber__owner_id=self.context['request'].user.owner_id,
            service=obj
        ).count()
        if count > 0:
            return True
        return False

    def get_virtual_value(self, obj):
        if not hasattr(obj, 'virtual_value'):
            return None
        return obj.virtual_value.balance


class CopyServiceReadOnlySerializer(BaseServiceReadOnlySerializer):
    risk = serializers.SerializerMethodField(read_only=True)
    api_key_binded = serializers.BooleanField(read_only=True)

    class Meta:
        model = Service
        fields = BaseServiceReadOnlySerializer.Meta.fields + (
            'risk',
            'balance',
            'copy_exchange',
            'api_key_binded',
            'vip_member_count'
        )

    def get_risk(self, obj):
        today = date.today()
        result = list()
        for i in range(4):
            start, end = previous_week_range(today)
            risk = DailyAggregatedPnl.objects.filter(
                date__range=[start, end],
                service_id=obj.id,
            ).aggregate(
                risk=Coalesce(
                    models.Min("percentage"),
                    0,
                    output_field=models.IntegerField()
                )
            )['risk']

            result.append(
                risk_evaluation(
                    abs(risk)
                )
            )
            today = today - timedelta(days=7)
        return max(result)


class CopyServiceDetailReadOnlySerializer(CopyServiceReadOnlySerializer):
    subscription_expire_time = serializers.DateTimeField(allow_null=True)

    class Meta(CopyServiceReadOnlySerializer.Meta):
        fields = CopyServiceReadOnlySerializer.Meta.fields + (
            'subscription_expire_time',
            'vip_member_count'
        )


class ServiceMouseHoverSerializer(BaseModelSerializer):
    service_owner = ProfileReadOnlySerializer(source="profile")
    win_rate = serializers.FloatField()
    closed_signals_count = serializers.IntegerField()
    coin = serializers.CharField()

    class Meta:
        model = Service
        fields = (
            'id',
            'service_owner',
            'win_rate',
            'closed_signals_count',
            'coin',

        )


class ServiceReadOnlySerializer(
    BaseServiceReadOnlySerializer
):
    row_number = serializers.SerializerMethodField()
    signal_count = serializers.IntegerField()
    closed_signals_count = serializers.IntegerField()
    win_rate = serializers.FloatField()
    service_owner = ProfileReadOnlySerializer(source="profile")
    _TEMP_CACHE_FOR_ROW_NUM = None

    class Meta(BaseServiceReadOnlySerializer.Meta):
        model = Service
        fields = BaseServiceReadOnlySerializer.Meta.fields + (
            'id',
            'row_number',
            'title',
            'description',
            'service_owner',
            'state',
            'service_type',
            'subscription_fee',
            'subscription_coin',
            'watch_list',
            'exchanges',
            'signal_count',
            'closed_signals_count',
            'win_rate',
            'has_trial',
            'copy_exchange',
        )

    def get_row_number(
            self,
            obj
    ):
        ranking_page_signals_limit = self.context["ranking_page_signals_limit"]
        today = datetime.today()
        if obj.state != ServiceStateChoices.PUBLISH:
            # NOTE: caches onces for every call, boosted performance almost 5x
            # TODO: this will get slow eventually, its better to store ranks in db
            if not self._TEMP_CACHE_FOR_ROW_NUM:
                subquery = Subquery(DailyROI.objects.filter(
                    roi_history__history_type=HistoryTypeChoices.MONTHLY,
                    roi_history__service=OuterRef('id')
                ).order_by('-number').values('percentage')[:1])
                try:
                    today_pnl = Subquery(DailyAggregatedPnl.objects.filter(
                        date=today,
                        service_id=OuterRef('id'),
                    ).values('percentage')[:1])
                except DailyAggregatedPnl.DoesNotExist:
                    print('inja')
                    today_pnl = 0
                subquery += today_pnl
                queryset = Service.objects.prefetch_related(
                    'service_signal'
                ).annotate(
                    total_signal=SubqueryCount(
                        TradingSignal.objects.filter(
                            sid_id=models.OuterRef("id"),
                            state=StatusChoice.CLOSE
                        ).values('id')
                    ),
                    monthly_roi=Coalesce(
                        subquery,
                        Value(0),
                        output_field=models.DecimalField(
                            max_digits=MAX_DIGIT,
                            decimal_places=DECIMAL_PLACE
                        )
                    ),
                    row_number=Window(
                        expression=Rank(),
                        order_by=F('monthly_roi').desc()
                    )
                ).filter(
                    ~Q(state=ServiceStateChoices.PUBLISH),
                    total_signal__gte=ranking_page_signals_limit,
                ).order_by('-monthly_roi').values_list('row_number', 'id', 'monthly_roi')
                dict_data = {}
                for i in queryset:
                    dict_data[i[1]] = i[0]
                self._TEMP_CACHE_FOR_ROW_NUM = dict_data
            row_num = self._TEMP_CACHE_FOR_ROW_NUM.get(obj.id)
            if row_num:
                return row_num
        return


class ServiceReadOnlyDetailSerializer(ServiceReadOnlySerializer):
    subscription_expire_time = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = Service
        fields = ServiceReadOnlySerializer.Meta.fields + (
            "subscription_expire_time",
            "vip_member_count"
        )


class ServiceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "title",
            'exchanges',
            'subscription_fee',
            'description',
            'watch_list',
            'has_trial'
        )
        read_only_fields = (
            'id',
        )
        extra_kwargs = {
            'subscription_fee': {'required': False}
        }

    def update(self, instance, validated_data):
        title = validated_data.get("title")
        if title:
            instance.profile.title = title
            instance.profile.save()
        return super().update(instance, validated_data)

    def to_internal_value(
            self,
            data
    ):
        return super(ServiceUpdateSerializer, self).to_internal_value(data)


class ServiceCreateSerializer(serializers.ModelSerializer):
    image_id = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Service
        fields = (
            "title",
            "link",
            "image_id",
            "service_type",
            "subscription_fee",
            "exchanges",
            "description",
            "watch_list",
            "has_trial",
        )

    def create(self, validated_data):
        profile = validated_data.pop("profile")
        image_id = validated_data.pop("image_id", None)
        title = validated_data.pop("title", None)
        service: Service = super().create(validated_data)
        service.title = title or profile.title
        service.image_id = image_id
        service.profile = profile
        service.save()
        return service


class ServiceMinimalReadOnlySerializer(BaseModelSerializer):
    service_owner = ProfileReadOnlySerializer(source="profile", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "title",
            "description",
            "service_owner",
            "subscription_fee"
        )
        read_only_fields = (
            'id',
            "title",
            "description",
            "subscription_fee"
        )


class ServiceRankingSerializer(serializers.Serializer):
    rank_number = serializers.IntegerField(
        source='row_number'
    )
    id = serializers.IntegerField()
    total_signal = serializers.IntegerField()
    profile = ProfileReadOnlySerializer()
    total_roi = serializers.DecimalField(
        max_digits=MAX_DIGIT,
        decimal_places=DECIMAL_PLACE
    )
    signals_count_in_range = serializers.IntegerField()
    mine = serializers.SerializerMethodField()
    _TEMP_PROFILE_OBJ = None

    def get_mine(self, obj):
        owner_id = self.context['request'].user.owner_id
        if not self._TEMP_PROFILE_OBJ:
            self._TEMP_PROFILE_OBJ = Profile.objects.get(owner_id=owner_id)
        if self._TEMP_PROFILE_OBJ.id == obj.profile.id:
            return True
        return False


class ActiveCampaignSerializer(serializers.Serializer):
    campaign_key = serializers.CharField()
    campaign_name_fa = serializers.CharField()


class TraderAccountStatusSerializer(serializers.Serializer):
    balance = serializers.FloatField()
    membership_long = serializers.IntegerField()
    trade_profit_sum = serializers.FloatField()
    copiers_profit_sum = serializers.FloatField()
