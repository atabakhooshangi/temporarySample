from django.contrib import admin


class CopySettingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'profile',
        'service',
        'margin',
        'take_profit_percentage',
        'stop_loss_percentage',
        'is_active'
    )
    list_editable = ['is_active']


class TradingOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "symbol",
        "type",
        "exchange",
        "position_id",
        "parent_order",
        "order_type",
        "side",
        "state",
        "price",
        "entry_point",
        "take_profit",
        "stop_loss",
        "position"
    )


class PositionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "side",
        "profile",
        "status",
        "closed_pnl",
        "unrealised_pnl",
        "avg_entry_price",
        "avg_exit_price",
    )  # TODO : add link to trading order