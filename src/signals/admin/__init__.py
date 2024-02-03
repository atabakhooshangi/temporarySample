from django.contrib import admin

from signals.models import (
    TradingSignal,
    ExchangeMarket,
    Exchange,
    Market,
    Comment,
    VendorFollower,
    UserFollowing,
    CoinDecimalNumber,
    SignalVirtualBalance
)
from .follow import UserFollowingAdmin, VendorFollowerAdmin
from .signal import TradingSignalAdmin, ExchangeMarketAdmin
from .coin import CoinDecimalNumberAdmin

admin.site.register(Exchange)
admin.site.register(Market)
admin.site.register(ExchangeMarket, ExchangeMarketAdmin)
admin.site.register(TradingSignal, TradingSignalAdmin)
admin.site.register(Comment)
admin.site.register(UserFollowing, UserFollowingAdmin)
admin.site.register(VendorFollower, VendorFollowerAdmin)
admin.site.register(CoinDecimalNumber, CoinDecimalNumberAdmin)
admin.site.register(SignalVirtualBalance)
