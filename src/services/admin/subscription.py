import datetime

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from django.contrib import admin

from core.base_model import BaseModelAdmin
from core.choice_field_types import ServiceStateChoices
from services.models import Service


class PublishedServiceFilter(admin.SimpleListFilter):
    title = _("published services")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "service_id"

    def lookups(self, request, model_admin):
        return [(c.id, c.__str__) for c in Service.objects.filter(state=ServiceStateChoices.PUBLISH).all()] + [
            ('not_published', 'Not Published')]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == 'not_published':
            return queryset.exclude(service__state=ServiceStateChoices.PUBLISH)
        return queryset.filter(service_id=self.value())


class SubscriptionAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "created_at",
        "service",
        "subscriber_title",
        "subscriber_username",
        "subscription_fee",
        "payment_type",
        "start_time",
        "expire_time",
        "tracking_code",
        "is_paid",
        "remaining_time"

    )
    list_filter = [
        PublishedServiceFilter,
        "payment_type",
        "is_paid",
        "subscriber_id",

    ]
    ordering = ('-updated_at',)

    def subscriber_title(self, obj):
        return obj.subscriber.title

    def subscriber_username(self, obj):
        return obj.subscriber.username

    def subscription_fee(self, obj):
        return obj.amount

    def remaining_time(self, obj):
        if not obj.expire_time or not obj.start_time:
            return
        if datetime.datetime.now() > obj.start_time:
            remaining = (obj.expire_time - datetime.datetime.now()).days
        else:
            remaining = (obj.expire_time - obj.start_time).days
        return remaining if remaining >= 0 else 0


class SubscriptionInvoiceAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "subscription",
        "ipg_track_id",
        "reference_id",
        "amount",
        "usdt_amount",
        "status",
        "description",
        "additional_data",
    )
    list_filter = (
        "status",
    )
    ordering = ('-updated_at',)
