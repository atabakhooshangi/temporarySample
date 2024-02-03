import django_filters
from django.db.models import Q
from django_filters import BaseInFilter
from django_filters.rest_framework import FilterSet

from services.models import Service, SubscriptionInvoice, Subscription
from django_filters.widgets import CSVWidget

from core.choice_field_types import SubscriptionPaymentTypeChoices
import operator
from django.db.models import Q
from functools import reduce


class ServiceFilter(FilterSet):
    free = django_filters.CharFilter(
        method='get_free_service'
    )
    exchange = BaseInFilter(
        widget=CSVWidget,
        method='get_exchange'
    )
    watch_list = BaseInFilter(
        widget=CSVWidget,
        method='get_watch_list'
    )

    class Meta:
        model = Service
        fields = [
            'subscription_coin',
            'service_type',
            'is_visible',
            'subscription_coin',
            'state',
            'free',
            'exchange',
            'watch_list'
        ]

    def get_free_service(self, queryset, name, value):
        if value == 'True':
            return queryset.filter(subscription_fee=0)
        elif value == 'False':
            return queryset.filter(~Q(subscription_fee=0))
        return queryset

    def get_exchange(self, queryset, name, value):
        if value:
            return queryset.filter(reduce(
                operator.or_,
                (Q(exchanges__contains=exchange) for exchange in value)
            ))
        return queryset

    def get_watch_list(self, queryset, name, value):
        if value:
            return queryset.filter(reduce(
                operator.or_,
                (Q(watch_list__contains=coin) for coin in value)
            ))
        return queryset


class SubscriptionInvoiceFilter(FilterSet):
    class Meta:
        model = SubscriptionInvoice
        fields = [
            'status',
            'subscription__payment_type',
        ]


class SubscriptionFilter(FilterSet):
    is_purchased = django_filters.BooleanFilter(
        method="filter_is_purchased"
    )
    class Meta:
        model = Subscription
        fields = [
            'payment_type',
            'start_time',
            'expire_time',
            'is_purchased',
            'is_paid',
        ]

    def filter_is_purchased(self, queryset, name, value):
        if value is not None:
            condition = dict(
                payment_type__in=(
                    SubscriptionPaymentTypeChoices.IRT_PAID,
                    SubscriptionPaymentTypeChoices.CRYPTO_PAID,
                    SubscriptionPaymentTypeChoices.CRYPTO_INTERNAL_PAID,
                    SubscriptionPaymentTypeChoices.CRYPTO_GATEWAY_PAID,
                )
            )
            if value == True:
                return queryset.filter(
                    **condition
                )
            else:
                return queryset.exclude(
                    **condition
                )
        return queryset
