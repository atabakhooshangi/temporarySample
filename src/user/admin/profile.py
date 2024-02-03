from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.base_model import BaseModelAdmin
from services.models import Subscription
from signals.models.follow import VendorFollower, UserFollowing


class ProfileAdmin(BaseModelAdmin):
    list_display = (
        "id",
        "owner_id",
        "title",
        "username",
        "description",
        "image",
        "is_vendor",
        "state",
        "follower",
        "following",
        "subscription"
    )
    list_filter = (
        "title",
        "username",
        "owner_id",
        "is_vendor",
        "created_at",
    )
    search_fields = (
        "username",
        "title",
        "description"
    )
    readonly_fields = ("follower", "following")

    def follower(self, obj):
        url = f"{reverse('admin:signals_vendorfollower_changelist')}?vendor_id__exact={obj.id}"
        return mark_safe(f"<a href={url}>{VendorFollower.objects.filter(vendor=obj).count()}</a>")

    def following(self, obj):
        url = f"{reverse('admin:signals_userfollowing_changelist')}?user_id__exact={obj.id}"
        return mark_safe(f'<a href="{url}">{UserFollowing.objects.filter(user=obj).count()}</a>')

    def subscription(self, obj):
        url = f"{reverse('admin:services_subscription_changelist')}?subscriber_id__exact={obj.id}"
        return mark_safe(f'<a href="{url}">{Subscription.objects.filter(subscriber=obj).count()}</a>')



class VendorProfileAnalyticAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "analytics"
    )

    search_fields = (
        "profile__username",
    )
