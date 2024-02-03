from django.contrib import admin

from copytrading.admin.apikey import ApiKeyAdmin, ProfileServiceApiKeyAdmin
from copytrading.admin.copy import TradingOrderAdmin, PositionAdmin, CopySettingAdmin
from copytrading.models import ApiKey, TradingOrder, Position, CopySetting, ProfileServiceApiKey

admin.site.register(ApiKey, ApiKeyAdmin)
admin.site.register(TradingOrder, TradingOrderAdmin)
admin.site.register(Position, PositionAdmin)
admin.site.register(CopySetting, CopySettingAdmin)
admin.site.register(ProfileServiceApiKey,ProfileServiceApiKeyAdmin)
