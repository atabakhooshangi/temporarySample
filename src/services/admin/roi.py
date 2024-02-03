from django.contrib import admin


class DailyROIAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "roi_history",
        "number",
        "history_type",
        "percentage",
        "date",
    )
    list_filter = (
        "roi_history__service",
        "roi_history__service__profile",
        "date",
    )
    search_fields = (
        "roi_history__history_type",
    )

    @admin.display(description='History type')
    def history_type(self, obj):
        return obj.roi_history.history_type

class ROIHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "service",
        "profile",
        "history_type",
        "updated_at",
    )
    list_filter = (
        "history_type",
        "service"
    )
    search_fields = (
        "service__title",
        "service__description",
        "service__profile__title",
        "service__profile__username",
    )


    @admin.display(description='Service vendor profile')
    def profile(self, obj):
        return obj.service.profile

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("service__profile", "service")

class DailyAggregatedPnlAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "service",
        "amount",
        "percentage",
        "date",
    )
    list_filter = (
        "date",
        "service"
    )
