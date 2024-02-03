from django.contrib import admin


class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'exchange', 'owner')
    list_filter = ('owner',)

    def owner(self, obj):
        return obj.user.username


class ProfileServiceApiKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "api_key", "service", "profile",)
