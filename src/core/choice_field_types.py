# Define all choices
from django.db import models


class TradingSignalType(models.TextChoices):
    FUTURES = "FUTURES", "futures"
    SPOT = "SPOT", "spot"


class TradingOrderType(
    models.TextChoices):  # ToDO : when inherit TradinSignalType get con not extent enumerations error
    FUTURES = "FUTURES", "futures"
    SPOT = "SPOT", "spot"


class PositionSideChoice(models.TextChoices):
    LONG = "LONG", "long"
    SHORT = "SHORT", "short"


class PositionChoice(models.TextChoices):
    LONG = "LONG", "long"
    SHORT = "SHORT", "short"


class StatusChoice(models.TextChoices):
    DRAFT = "DRAFT", "draft"
    TEST = "TEST", "test"
    PUBLISH = "PUBLISH", "publish"
    START = "START", "start"
    CLOSE = "CLOSE", "close"
    DELETED = "DELETED", "deleted"


class ServiceTypeChoices(models.TextChoices):
    SIGNAL = "SIGNAL", "signal"
    COPY = "COPY", "copy"


class CoinChoices(models.TextChoices):
    USDT = "USDT", "usdt"
    IRR = "IRR", "irr"


class ProfileStateChoices(models.TextChoices):
    PUBLISH = "PUBLISH", "publish"


class PnLTypeChoices(models.TextChoices):
    PROFIT = "PROFIT", "profit"
    LOSS = "LOSS", "loss"


class HistoryTypeChoices(models.TextChoices):
    WEEKLY = "WEEKLY", "weekly"
    TWO_WEEKLY = "TWO_WEEKLY", "two_weekly"
    MONTHLY = "MONTHLY", "monthly"
    TWO_MONTHLY = "TWO_MONTHLY", "two_monthly"
    THREE_MONTHLY = "THREE_MONTHLY", "three_monthly"
    OVERALLY = "OVERALLY", "overally"


class CloseReasonTradingSignalChoices(models.TextChoices):
    HIT_TP_1 = "HIT_TP", "hit_tp_1"
    HIT_TP_2 = "HIT_TP_2", "hit_tp_2"
    HIT_SL = "HIT_SL", "hit_sl"
    MANUAL_CLOSE = "MANUAL_CLOSE", "manual_close"
    CLOSE = 'CLOSE', 'close'


class AuthenticationLevelChoices(models.TextChoices):
    BASIC = 'BASIC'
    LEVEL_ONE = 'LEVEL_ONE'
    LEVEL_TWO = 'LEVEL_TWO'


class SubscriptionPaymentTypeChoices(models.TextChoices):
    FREE = 'FREE'
    TRIAL = 'TRIAL'
    IRT_PAID = 'IRT_PAID'
    CRYPTO_PAID = 'CRYPTO_PAID'
    CRYPTO_GATEWAY_PAID = 'CRYPTO_GATEWAY_PAID'
    CRYPTO_INTERNAL_PAID = 'CRYPTO_INTERNAL_PAID'


class MediaType(models.TextChoices):
    IMAGE = 'image', 'image'


class BucketTypeChoices(models.TextChoices):
    IMAGE = 'image', 'image'
    CHARTS = 'charts', 'charts'


class ServiceStateChoices(models.TextChoices):
    TRACKING = 'TRACKING', 'tracking'
    REQUESTED = 'REQUESTED', 'requested'
    PENDING = 'PENDING', 'pending'
    PUBLISH = 'PUBLISH', 'publish'


class SubscriptionInvoiceStatusChoices(models.TextChoices):
    PENDING = 'PENDING'
    SUCCESSFUL = 'SUCCESSFUL'
    FAILED = 'FAILED'
    EXPIRED = 'EXPIRED'


class ExchangeChoices(models.TextChoices):
    COINEX = 'COINEX'
    BYBIT = 'BYBIT'
    KUCOIN = 'KUCOIN'
    BINGX = 'BINGX'
    NOBITEX = 'NOBITEX'


class MessageCategoryChoices(models.TextChoices):
    """
        Message categories that will be produced in kafka
    """
    SOCIAL_SERVICE_SUBSCRIPTION = 'social_service_subscription'
    SOCIAL_SIGNAL_COMMENT = 'social_signal_comment'
    SOCIAL_SIGNAL_CLOSE = 'social_signal_close'
    SOCIAL_SIGNAL_UPDATE = 'social_signal_update'
    SOCIAL_SIGNAL_DELETE = 'social_signal_delete'


class OrderSideChoices(models.TextChoices):
    BUY = 'BUY'
    SELL = 'SELL'


class OrderTypeChoices(models.TextChoices):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TradingOrderStatusChoices(models.TextChoices):
    NEW = "New"
    ACTIVE = "Active"
    PARTIALLY_FILLED = "PartiallyFilled"
    PARTIALLY_FILLED_CANCELED = "PartiallyFilledCanceled"
    FILLED = "FILLED"
    CANCELLED = "Cancelled"
    TRIGGERED = "Triggered"
    OPEN = "open"
    CLOSED = 'closed'
    FAILED = "failed"
    X_OPEN = "x_open"
    X_CLOSED = 'X_CLOSED'  # where order have been closed, but the corresponding closure information could not be found on the exchange.
    OPPOSE_SIDE_MARKET_CLOSE = 'OpposeSideMarketClose'


class PositionStatusChoices(models.TextChoices):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELED = "CANCELED"
    X_CLOSED = 'X_CLOSED'  # where positions have been closed, but the corresponding closure information could not be found on the exchange.


class CopyExchangeChoices(models.TextChoices):
    BYBIT = 'BYBIT', 'BYBIT'
    KUCOIN = 'KUCOIN', 'KUCOIN'
    BINGX = 'BINGX', 'BINGX'
