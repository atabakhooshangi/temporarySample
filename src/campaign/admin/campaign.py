from django.contrib import admin
from django.core.cache import cache
from core.utils import ExtendedActionsMixin


class CampaignAdmin(ExtendedActionsMixin, admin.ModelAdmin):
    list_display = ("id", "campaign_key", "show", "start_date", "end_date")
    actions = ['clear_ranking_cache']
    extended_actions = ('clear_ranking_cache',)

    def clear_ranking_cache(self, request, queryset):
        ranking_caches = cache.keys("*ranking*")
        for item in ranking_caches:
            cache.delete(item)
