from datetime import datetime

import django_filters
from django.db import models
from django.db.models import Q
from django_filters import BaseInFilter
from django_filters.rest_framework import FilterSet
from django_filters.widgets import CSVWidget

from copytrading.models import TradingOrder
from core.choice_field_types import StatusChoice, TradingOrderStatusChoices, TradingOrderType, PositionStatusChoices
from signals.models import TradingSignal
from user.models import Profile


class TradingSignalFilter(FilterSet):
    state = django_filters.filters.CharFilter(
        field_name='state',
        method='get_state',
    )
    exchange = BaseInFilter(
        widget=CSVWidget,
        method='get_exchange'
    )
    coin = BaseInFilter(
        widget=CSVWidget,
        method='get_coin'
    )
    bought = django_filters.filters.BooleanFilter(
        field_name='bought',
        method='get_bought'
    )

    class Meta:
        model = TradingSignal
        fields = (
            'sid__profile_id',
            'sid__profile__username',
            'sid__profile__title',
            'sid',
            'sid__title',
            'type',
            'position',
            'state',
            'vip',
            'type',
            'position',
            'exchange',
            'bought'
        )

    def get_state(self, queryset, name, value):
        if value:
            if value == 'OPEN':
                return queryset.filter(
                    ~Q(state=StatusChoice.CLOSE),
                    ~Q(state=StatusChoice.DELETED),
                    Q(is_deleted=False)
                )
            return queryset.filter(state=value)
        return queryset

    def get_exchange(self, queryset, name, value):
        # TODO: solve problem don't show null value
        if value:
            return queryset.filter(
                exchange_market__exchange_name__in=value,
                exchange_market__exchange_name__isnull=False
            )
        return queryset

    def get_coin(self, queryset, name, value):
        # TODO: solve problem don't show null value
        if value:
            return queryset.filter(
                exchange_market__base_currency__in=value,
                exchange_market__base_currency__isnull=False
            )
        return queryset

    def get_bought(
            self,
            queryset,
            name,
            value
    ):
        if value:
            return queryset.filter(
                sid__subscription__subscriber=Profile.objects.get(owner_id=self.request.user.owner_id),
                sid__subscription__is_paid=True,
                sid__subscription__expire_time__gte=datetime.now())
        return queryset


class SignalCopyFilter(FilterSet):
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
                models.Q(type=TradingOrderType.FUTURES) &
                models.Q(state__in=[TradingOrderStatusChoices.OPEN, TradingOrderStatusChoices.X_OPEN]) |
                models.Q(
                    models.Q(state=TradingOrderStatusChoices.CLOSED) &
                    models.Q(position__status=PositionStatusChoices.OPEN)
                )
                | models.Q(type=TradingOrderType.SPOT) & models.Q(state=TradingOrderStatusChoices.OPEN))

        elif value == 'CLOSED':
            queryset = queryset.filter(
                models.Q(type=TradingOrderType.FUTURES) &
                models.Q(position__status__in=[PositionStatusChoices.CLOSED,
                                               PositionStatusChoices.CANCELED,
                                               PositionStatusChoices.X_CLOSED])

                | models.Q(type=TradingOrderType.SPOT) & models.Q(state=TradingOrderStatusChoices.CLOSED)
            )
        return queryset
