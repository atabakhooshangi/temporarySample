from copy import deepcopy

from django.contrib import admin
from django.db.models import Q
from import_export.admin import ImportExportModelAdmin

from core.base_model import BaseModelAdmin
from core.choice_field_types import (
    StatusChoice,
    CloseReasonTradingSignalChoices
)
from core.utils import convertor
from django.db import models
from signals.models import ExchangeMarket, TradingSignal
from signals.pnl import SignalPnLCalculator
from signals.tasks import fetch_update_markets
from signals.utils import market_fetcher


class OpenSignalFilter(admin.SimpleListFilter):
    title = 'Open Signals'
    parameter_name = 'open_signals'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
            ('No', 'No')
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(
                state__in=(StatusChoice.PUBLISH, StatusChoice.START),
                is_deleted=False)
        elif self.value() == 'No':
            return queryset.filter(
                ~Q(Q(state=StatusChoice.PUBLISH) | Q(state=StatusChoice.START)))
        return queryset


@admin.action(description='Deactivate multiple exchange market')
def deactivate(
        modeladmin,
        request,
        queryset
):
    queryset.update(is_active=False)


@admin.action(description='Activate multiple exchange market')
def activate(
        modeladmin,
        request,
        queryset
):
    queryset.update(is_active=True)


@admin.action(description='Fetch and Update all Markets')
def market_fetch(
        modeladmin,
        request,
        queryset
):
    fetch_update_markets.delay()


@admin.action(description='Remove duplicate exchange market')
def remove_duplicates(
        modeladmin,
        request,
        queryset
):
    exchange_markets = deepcopy(ExchangeMarket.objects.all())
    for market in exchange_markets:
        dup_markets = ExchangeMarket.objects.filter(
            base_currency=market.base_currency,
            quote_currency=market.quote_currency,
            exchange_name=market.exchange_name,
            market_type=market.market_type
        ).annotate(
            signals_count=models.Count('exchange_market_signals'),
        ).order_by('-signals_count')
        if len(dup_markets) > 1:
            dup_market = dup_markets[0]
            signals = TradingSignal.objects.filter(exchange_market__in=dup_markets[1:])
            signals.update(exchange_market=dup_market)
            dup_markets.exclude(id=dup_market.id).delete()


class TradingSignalAdmin(
    BaseModelAdmin
):
    # TODO: convert create_at to jalali date
    list_display = (
        'id',
        'is_deleted',
        'owner',
        'reference_id',
        'type',
        'position',
        'leverage',
        'result',
        'pnl_percentage',
        'pnl_amount',
        'created_at',
        'start_datetime',
        'closed_datetime',
        'exchange_market',
        'show_entry_point',
        'hit_entry_point',
        'show_take_profit_1',
        'hit_tp_1',
        'show_take_profit_2',
        'hit_tp_2',
        'show_stop_los',
        'hit_sl',
        'closed_datetime'
    )

    list_filter = (
        'sid__profile',
        'sid',
        'state',
        'type',
        'position',
        'exchange_market__exchange_name',
        OpenSignalFilter
    )
    autocomplete_fields = ['exchange_market']

    def show_entry_point(self, obj):
        if obj.entry_point:
            return convertor(
                obj.entry_point,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return obj.entry_point

    def show_take_profit_1(self, obj):
        if obj.take_profit_1:
            return convertor(
                obj.take_profit_1,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return obj.take_profit_1

    def show_take_profit_2(self, obj):
        if obj.take_profit_2:
            return convertor(
                obj.take_profit_2,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return obj.take_profit_2

    def show_stop_los(self, obj):
        if obj.stop_los:
            return convertor(
                obj.stop_los,
                obj.exchange_market.quote_currency,
                obj.exchange_market.base_currency,
                'decimal'
            )
        return obj.stop_los

    def hit_entry_point(self, obj):
        return obj.entry_point_hit_datetime is not None

    def hit_tp_1(self, obj):
        return obj.take_profit_1_hit_datetime is not None

    def hit_tp_2(self, obj):
        return obj.take_profit_2_hit_datetime is not None

    def hit_sl(self, obj):
        return obj.stop_los_hit_datetime is not None

    def owner(self, obj):
        return obj.sid.profile

    def result(self, obj):
        if obj.state == StatusChoice.CLOSE:
            if obj.take_profit_1_hit_datetime:
                return CloseReasonTradingSignalChoices.HIT_TP_1
            elif obj.take_profit_2_hit_datetime:
                return CloseReasonTradingSignalChoices.HIT_TP_2
            elif obj.stop_los_hit_datetime:
                return CloseReasonTradingSignalChoices.HIT_SL
        return obj.state

    def save_form(self, request, form, change):
        if change and 'state' in form.changed_data and form.data['state'] == StatusChoice.START:
            if 'start_datetime' not in form.changed_data or 'entry_point_hit_datetime' not in form.changed_data:
                raise Exception("can't start signal without set start_datetime and entry_point_hit_datetime field")

        elif change and 'state' in form.changed_data and form.data['state'] == StatusChoice.CLOSE:
            if 'closed_datetime' not in form.changed_data:
                raise Exception("can't close signal without setting closed_datetime field")

            missing_hit_fields = [
                'stop_los_hit_datetime',
                'take_profit_2_hit_datetime',
                'take_profit_1_hit_datetime',
                'manual_closure_price'
            ]
            if all(field not in form.changed_data for field in missing_hit_fields):
                raise Exception(
                    f"Can't close the signal without setting one of the following fields:: {', '.join(missing_hit_fields)}")
        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        if 'state' in form.changed_data and (
                form.data['state'] in [StatusChoice.START, StatusChoice.CLOSE, StatusChoice.DELETED]):
            return super().save_model(request, obj, form, change)
        SignalPnLCalculator(obj,
                            obj.exchange_market.quote_currency,
                            obj.exchange_market.base_currency).possible_pnl_calculator()
        return super().save_model(request, obj, form, change)


class ExchangeMarketAdmin(
    ImportExportModelAdmin,
):
    list_display = (
        "id",
        "exchange_name",
        "coin_pair",
        "coin_name",
        "base_currency",
        "quote_currency",
        "market_type",
        "futures_symbol",
        "is_active",
        "tick_size"
    )
    search_fields = (
        "exchange_name",
        "coin_pair",
        "base_currency"
    )
    list_filter = (
        "market_type",
        "exchange_name",
    )
    actions = [deactivate, activate, market_fetch, remove_duplicates]
