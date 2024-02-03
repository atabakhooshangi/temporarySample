import json
from datetime import date, timedelta

import requests
from dateutil.relativedelta import relativedelta
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Value, OuterRef, Window, F
from django.db.models.functions import ExtractDay, Cast, Round, Coalesce, Rank, Abs

from core.api_gateways import ProducerClientGateway, KafkaTopic
from core.base_model import BaseModelAdmin
from core.choice_field_types import StatusChoice, ServiceTypeChoices, ServiceStateChoices
from core.settings import BASE_INTERNAL_URL
from core.sql_functions import SubquerySum, RoundWithPlaces
from services.models import Service, DailyAggregatedPnl
from user.models import Profile

from services.calc_utils import (
    calc_pnl,
    calc_roi,
    calc_today_aggregated_pnl,
    calc_aggregated_pnl,
    correct_frozen_balances, correct_total_balances
)


@admin.action(description='pnl calculation')
def pnl_calculation(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    calc_pnl(ids)
    return True


@admin.action(description='aggregated pnl')
def aggregate_pnl_calculation(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    calc_aggregated_pnl(ids)
    return True

@admin.action(description='correct_frozen_balances')
def correct_frozen_balance(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    correct_frozen_balances(ids)
    return True

@admin.action(description='correct_total_balance')
def correct_total_balance(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    correct_total_balances(ids)
    return True


@admin.action(description='today aggregated pnl')
def today_aggregate_pnl_calculation(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    calc_today_aggregated_pnl(ids)
    return True


@admin.action(description='roi')
def roi(modeladmin, request, queryset):
    ids = [str(i) for i in queryset.values_list('id', flat=True)]
    calc_roi(ids)
    return True


class ServiceAdmin(BaseModelAdmin):
    statistics = dict()
    avg_pnl = dict()
    count = 0
    list_display = (
        'id',
        "title",
        "profile",
        "profile_title",
        "profile_username",
        "is_visible",
        "state",
        "service_type",
        "coin",
        "subscription_coin",
        "subscription_fee",
        "signals_count",
        "vip_signals_count",
        "avg_weekly_signals",
        "win_rate",
        "avg_open_days",
        "profit_to_loss",
        "avg_pnl_percentage",
        "in_loss_signal_avg_loss",
        "profitable_signal_avg_profit",
        "image",
        "link",
        "description",
    )

    list_filter = (
        "service_type",
        "coin",
        "is_visible",
        "subscription_coin",
        "state",
        "id",
        "profile",
    )
    search_fields = (
        "title",
        "link",
        "description",
        "id"
    )

    def save_model(self, request, obj, form, change):
        sms_case_states_template = {
            ServiceStateChoices.REQUESTED.value: "vendor-requested",
            ServiceStateChoices.PUBLISH.value: "vendor-publish"
        }
        if change:
            try:
                old = Service.objects.get(id=obj.id)
            except ObjectDoesNotExist as e:
                raise e
            if old.state != obj.state and obj.state in sms_case_states_template.keys():
                data = {
                    "owner_id": obj.profile.owner_id,
                    "template": sms_case_states_template[obj.state]
                }
                ProducerClientGateway().produce(
                    topic=KafkaTopic.VENDOR_SMS,
                    message=json.dumps(data)
                )
        super(ServiceAdmin, self).save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False

    @classmethod
    def _statistics(cls, obj):
        today = date.today()
        weeks_since_profile_creation = (date.today() - Profile.objects.get(owner_id=obj.profile.id,
                                                                           ).created_at.date()).days // 7 + 1
        base_queryset = obj.service_signals.all()
        statistics = base_queryset.annotate(
            open_duration=(
                    models.F("closed_datetime") - models.F("start_datetime")
            ),
        ).aggregate(
            signals_count=models.Count("id"),
            closed_signals_count=models.Count(
                "id", filter=models.Q(
                    state=StatusChoice.CLOSE
                )
            ),
            closed_signals_pnl_amount_gt_zero_count=models.Count(
                "id",
                filter=models.Q(
                    pnl_amount__gt=0,
                    state=StatusChoice.CLOSE,
                )
            ),
            vip_signals_count=models.Count(
                "id",
                filter=models.Q(vip=True)
            ),
            avg_weekly_signals=models.Count("id") / weeks_since_profile_creation,
            profit_to_loss=(
                    models.Sum("pnl_percentage", filter=models.Q(
                        pnl_percentage__gte=0
                    )) * 100 /
                    models.Sum("pnl_percentage", filter=models.Q(
                        pnl_percentage__lt=0
                    ))
            ),
            avg_pnl_percentage=models.Avg("pnl_percentage"),
            avg_open_days=ExtractDay(models.Avg("open_duration")),

        )
        statistics['win_rate'] = None
        if statistics.get('closed_signals_count') != 0:
            statistics['win_rate'] = (statistics.get('closed_signals_pnl_amount_gt_zero_count') * 100 /
                                      statistics.get('closed_signals_count'))
        cls.statistics[obj.id] = statistics
        return statistics

    @classmethod
    def _avg_pnl(cls, obj):
        result_avg_pnl = obj.service_signals.filter(state=StatusChoice.CLOSE).aggregate(
            in_loss_signal_avg_loss=Abs(
                RoundWithPlaces(
                    models.Avg(
                        "pnl_percentage",
                        filter=models.Q(
                            pnl_amount__lt=0
                        )
                    )
                )
            ),
            profitable_signal_avg_profit=Abs(
                RoundWithPlaces(
                    models.Avg(
                        "pnl_percentage",
                        filter=models.Q(
                            pnl_amount__gt=0
                        )
                    )
                )
            )
        )
        cls.avg_pnl[obj.id] = result_avg_pnl
        return result_avg_pnl

    def profile_title(self, obj):
        return obj.profile.title

    def profile_username(self, obj):
        return obj.profile.username

    def signals_count(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['signals_count']
        return self._statistics(obj)['signals_count']

    def vip_signals_count(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['vip_signals_count']
        return self._statistics(obj)['vip_signals_count']

    def avg_weekly_signals(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['avg_weekly_signals']
        return self._statistics(obj)['avg_weekly_signals']

    def win_rate(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['win_rate']
        return self._statistics(obj)['win_rate']

    def avg_open_days(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['avg_open_days']
        return self._statistics(obj)['avg_open_days']

    def profit_to_loss(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['profit_to_loss']
        return self._statistics(obj)['profit_to_loss']

    def avg_pnl_percentage(self, obj):
        if obj.id in self.statistics:
            return self.statistics[obj.id]['avg_pnl_percentage']
        return self._statistics(obj)['avg_pnl_percentage']

    def in_loss_signal_avg_loss(self, obj):
        if obj.id in self.avg_pnl:
            return self.avg_pnl[obj.id]['in_loss_signal_avg_loss']
        return self._avg_pnl(obj)['in_loss_signal_avg_loss']

    def profitable_signal_avg_profit(self, obj):
        if obj.id in self.avg_pnl:
            return self.avg_pnl[obj.id]['profitable_signal_avg_profit']
        return self._avg_pnl(obj)['profitable_signal_avg_profit']

    actions = [
        pnl_calculation,
        aggregate_pnl_calculation,
        today_aggregate_pnl_calculation,
        roi,
        correct_frozen_balance,
        correct_total_balance
    ]


class ServiceRank(ServiceAdmin):
    def get_queryset(self, request):
        today = date.today()
        return self.model.objects.filter(service_type=ServiceTypeChoices.SIGNAL).annotate(
            total_roi=Coalesce(SubquerySum(
                DailyAggregatedPnl.objects.filter(
                    service_id=OuterRef('id'),
                    date__range=[today - relativedelta(years=1), today - timedelta(days=1)]
                ),
                'percentage'
            ),
                Value(0),
                output_field=models.DecimalField(max_digits=5, decimal_places=2)
            ),
            monthly_roi=Coalesce(SubquerySum(
                DailyAggregatedPnl.objects.filter(
                    service_id=OuterRef('id'),
                    date__range=[today - timedelta(days=30), today - timedelta(days=1)]
                ),
                'percentage'
            ),
                Value(0),
                output_field=models.DecimalField(max_digits=5, decimal_places=2)
            ),
            row_number_base_monthly_roi=Window(
                expression=Rank(),
                order_by=F('monthly_roi').desc()
            ),
            row_number_base_total_roi=Window(
                expression=Rank(),
                order_by=F('total_roi').desc()
            )
        )

    @classmethod
    def _pnl(cls):
        today = date.today()
        queryset = Service.objects.filter(service_type=ServiceTypeChoices.SIGNAL).annotate(
            total_roi=Coalesce(SubquerySum(
                DailyAggregatedPnl.objects.filter(
                    service_id=OuterRef('id'),
                    date__range=[today - relativedelta(years=1), today - timedelta(days=1)]
                ),
                'percentage'
            ),
                Value(0),
                output_field=models.FloatField()
            ),
            monthly_roi=Coalesce(SubquerySum(
                DailyAggregatedPnl.objects.filter(
                    service_id=OuterRef('id'),
                    date__range=[today - timedelta(days=30), today - timedelta(days=1)]
                ),
                'percentage'
            ),
                Value(0),
                output_field=models.FloatField()
            ),
            row_number_base_monthly_roi=Window(
                expression=Rank(),
                order_by=F('monthly_roi').desc()
            ),
            row_number_base_total_roi=Window(
                expression=Rank(),
                order_by=F('total_roi').desc()
            )
        )
        return queryset

    list_display = (
        'id',
        'title',
        'service_type',
        'state',
        'signals_count',
        'total_roi',
        'monthly_roi',
        'row_number_base_monthly_roi',
        'row_number_base_total_roi'
    )

    def monthly_roi(self, obj):
        try:
            return round(self._pnl().get(id=obj.id).monthly_roi, 2)
        except:
            raise Exception

    def total_roi(self, obj):
        try:
            return round(self._pnl().get(id=obj.id).total_roi, 2)

        except:
            raise Exception

    def row_number_base_monthly_roi(self, obj):
        queryset = self._pnl().values_list('row_number_base_monthly_roi', 'id')
        find_obj = [v[0] for v in queryset if v[1] == obj.id]
        if find_obj:
            return find_obj[0]

    def row_number_base_total_roi(self, obj):
        queryset = self._pnl().values_list('row_number_base_total_roi', 'id')
        find_obj = [v[0] for v in queryset if v[1] == obj.id]
        if find_obj:
            return find_obj[0]

    row_number_base_monthly_roi.admin_order_field = 'row_number_base_monthly_roi'
    row_number_base_total_roi.admin_order_field = 'row_number_base_total_roi'
