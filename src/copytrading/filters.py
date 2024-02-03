import django_filters
from django.db import models
from django_filters import BaseInFilter
from django_filters.rest_framework import FilterSet
from django_filters.widgets import CSVWidget

from copytrading.models import Position, TradingOrder
from core.choice_field_types import TradingOrderStatusChoices, PositionStatusChoices


class PositionFilterSet(FilterSet):
    exchange = BaseInFilter(
        widget=CSVWidget,
        method='get_exchange'
    )
    state = django_filters.filters.CharFilter(
        field_name='state',
        method='get_state',
    )

    class Meta:
        model = Position
        fields = (
            "id",
            "side",
            "status",
            "closed_pnl",
            "unrealised_pnl",
            "avg_entry_price",
            "avg_exit_price",
            "closed_datetime",
            "service__id",
            "state"
        )

    def get_exchange(self, queryset, name, value):
        if value:
            return queryset.filter(
                trading_order__exchange_name__in=value,
            )
        return queryset

    def get_state(self, queryset, name, value):
        if value == 'OPEN':
            queryset = queryset.filter(
                status__in=[
                    PositionStatusChoices.OPEN,
                ])
        elif value == 'CLOSED':
            queryset = queryset.filter(
                status__in=[
                    PositionStatusChoices.CLOSED,
                    PositionStatusChoices.CANCELED,
                    PositionStatusChoices.X_CLOSED
                ])
        return queryset


class TradingOrderFilterSet(FilterSet):
    state = django_filters.filters.CharFilter(
        field_name='state',
        method='get_state',
    )

    class Meta:
        model = TradingOrder
        fields = ('state',)

    def get_state(self, queryset, name, value):
        if value == 'OPEN':
            queryset = queryset.filter(
                state__in=[
                    TradingOrderStatusChoices.OPEN,
                    TradingOrderStatusChoices.X_OPEN
                ])
        elif value == 'CLOSED':
            queryset = queryset.filter(
                state__in=[
                    TradingOrderStatusChoices.CLOSED,
                    TradingOrderStatusChoices.CANCELLED,
                    TradingOrderStatusChoices.X_CLOSED,
                    TradingOrderStatusChoices.FILLED
                ])
        return queryset
