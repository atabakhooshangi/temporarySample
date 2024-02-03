from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

from core.base_model import BaseModelClass
from core.choice_field_types import (
    TradingSignalType,
    StatusChoice,
    PnLTypeChoices,
    PositionChoice,
    CloseReasonTradingSignalChoices,
)


class SignalResultChoiceTypes(models.TextChoices):
    CLOSED = "CLOSED", "closed"
    TP1 = "TP1", "tp1"
    TP2 = "TP2", "tp2"
    SL = "SL", "sl"


class CustomTradingSignalManager(models.Manager):

    def descendants(self, pk, include_self=True):
        result = list()
        signal = self.get(id=pk)
        if include_self:
            result.append(signal)
        if hasattr(signal, 'parent'):
            result.extend(self.descendants(signal.parent.id, include_self=True))
        return result

    def leaf(self, pk):
        signal = self.get(id=pk)
        if signal.edited_datetime:
            return self.leaf(pk=signal.child.id)
        return signal

    def root(self, pk):
        try:
            signal = self.get(child_id=pk)
            if signal.edited_datetime and signal.child:
                signal = self.root(pk=signal.id)
        except:
            signal = self.get(id=pk)
        return signal

    def get_queryset(self):
        return super().get_queryset()


class TradingSignalManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(
            Q(edited_datetime__isnull=False) |
            Q(child_id__isnull=False)
        )


class TradingSignal(BaseModelClass):
    child = models.OneToOneField(
        to='self',
        related_name='parent',
        related_query_name='parents',
        verbose_name='Child Id',
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    edited_datetime = models.DateTimeField(
        verbose_name="Edited datetime",
        null=True,
        blank=True
    )
    sid = models.ForeignKey(
        to='services.service',
        on_delete=models.CASCADE,
        related_name='service_signals',
        related_query_name='service_signal',
        verbose_name='Service id',
        db_index=True
    )
    type = models.CharField(
        max_length=255,
        choices=TradingSignalType.choices,
        default=TradingSignalType.SPOT,
        verbose_name='Type'
    )
    exchange_market = models.ForeignKey(
        to='ExchangeMarket',
        related_name='exchange_market_signals',
        verbose_name='Exchange market',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    position = models.CharField(
        max_length=255,
        choices=PositionChoice.choices,
        blank=True,
        null=True,
        verbose_name='Position',
        default=None
    )
    leverage = models.FloatField(
        default=1,
        verbose_name='Leverage',

    )
    percentage_of_fund = models.FloatField(
        verbose_name='Percentage of fund',
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        default=100
    )
    entry_point = models.BigIntegerField(
        default=0,
        verbose_name='Entry point'

    )
    entry_point_hit_datetime = models.DateTimeField(
        verbose_name="Entry point hit datetime",
        null=True,
        blank=True
    )
    take_profit_1 = models.PositiveBigIntegerField(
        null=False,
        verbose_name='Take profit 1'
    )
    take_profit_1_hit_datetime = models.DateTimeField(
        verbose_name="Take profit 1 hit datetime",
        null=True,
        blank=True
    )
    take_profit_2 = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name='Take_profit-2'
    )
    take_profit_2_hit_datetime = models.DateTimeField(
        verbose_name="Take profit 2 hit datetime",
        null=True,
        blank=True
    )
    volume = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='Volume',
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    stop_los = models.PositiveBigIntegerField(
        verbose_name='Stop los'
    )  # TODO: what is the concept
    stop_los_hit_datetime = models.DateTimeField(
        verbose_name="Stop loss hit datetime",
        null=True,
        blank=True
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    image = models.ForeignKey(
        to="media.Media",
        verbose_name="Signal image",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    state = models.CharField(
        max_length=256,
        choices=StatusChoice.choices,
        default=StatusChoice.PUBLISH,
        verbose_name='State',
        db_index=True
    )
    manual_closure_price = models.FloatField(
        verbose_name="Manual closure price",
        null=True,
        blank=True,
    )
    start_datetime = models.DateTimeField(
        verbose_name="Start datetime",
        null=True,
        blank=True
    )
    closed_datetime = models.DateTimeField(
        verbose_name="Closed datetime",
        null=True,
        blank=True,
    )
    vip = models.BooleanField(
        default=False,
        verbose_name='Vip'
    )
    pnl_percentage = models.FloatField(
        verbose_name="Pnl percentage",
        null=True,
        blank=True,
        db_index=True
    )
    pnl_amount = models.FloatField(
        verbose_name="Pnl amount",
        null=True,
        blank=True,
    )
    max_pnl_percentage = models.FloatField(
        verbose_name="Max Pnl amount",
        null=True,
        blank=True,
    )
    min_pnl_percentage = models.FloatField(
        verbose_name="Min Pnl amount",
        null=True,
        blank=True,
    )

    virtual_value = models.FloatField(
        verbose_name="Virtual Value",
        default=0
    )

    objects = TradingSignalManager()
    custom_objects = CustomTradingSignalManager()

    @property
    def pnl_type(self):
        if self.pnl_amount >= 0:
            return PnLTypeChoices.PROFIT
        return PnLTypeChoices.LOSS

    @property
    def reference_id(self):
        """a unique reference id for this signal"""
        return f"SIG-{self.sid_id}-{self.id}"

    @property
    def edited(self):
        if not self.child and self.parent:
            return True
        return False

    @property
    def signal_result(self):
        if self.manual_closure_price:
            return SignalResultChoiceTypes.CLOSED
        if self.stop_los_hit_datetime:
            return SignalResultChoiceTypes.SL
        if self.take_profit_2_hit_datetime:
            return SignalResultChoiceTypes.TP2
        if self.take_profit_1_hit_datetime:
            return SignalResultChoiceTypes.TP1
        return SignalResultChoiceTypes.CLOSED

    @property
    def trading_signal_hit(self):
        hit_value = None
        if self.closed_datetime:
            hit_value = CloseReasonTradingSignalChoices.CLOSE
            if self.take_profit_1_hit_datetime:
                hit_value = CloseReasonTradingSignalChoices.HIT_TP_1
            if self.take_profit_2_hit_datetime:
                hit_value = CloseReasonTradingSignalChoices.HIT_TP_2
            if self.stop_los_hit_datetime:
                hit_value = CloseReasonTradingSignalChoices.HIT_SL
            if self.manual_closure_price:
                hit_value = CloseReasonTradingSignalChoices.MANUAL_CLOSE
            return hit_value
        return self.state

    class Meta:
        verbose_name = 'signals'
        verbose_name_plural = 'trading-signals'
        ordering = ('-created_at',)


class Market(BaseModelClass):
    """
    TODO: this model is deprecated remove it later
    """
    primary_coin = models.CharField(
        max_length=50,
        verbose_name='Primary coin'
    )  # TODO: use the enum
    secoundary_coin = models.CharField(
        max_length=50,
        verbose_name='Secondary coin'
    )  # TODO: use the enum

    # image  #TODO: relation with image model.

    @property
    def market_code(self):
        return f'{self.primary_coin}/{self.secoundary_coin}'

    class Meta:
        verbose_name = 'market'
        verbose_name_plural = 'markets'
        ordering = ('created_at',)

    def __str__(self):
        return self.market_code


class Exchange(BaseModelClass):
    """
    TODO: this model is deprecated remove it later
    """
    name = models.CharField(
        max_length=256,
        verbose_name='Name'
    )
    market = models.ManyToManyField(
        to='Market',
        related_name='exchanges',
        related_query_name='exchanges',
        verbose_name='Market'
    )

    # image  #TODO: relation with image model.

    class Meta:
        verbose_name = 'exchange'
        verbose_name_plural = 'exchanges'


class ExchangeMarket(BaseModelClass):
    exchange_name = models.CharField(
        verbose_name='Exchange name',
        max_length=32,
    )
    coin_pair = models.CharField(
        verbose_name="Coin pair",
        max_length=32,
    )
    coin_name = models.CharField(
        verbose_name="Coin display name",
        max_length=32
    )
    base_currency = models.CharField(
        verbose_name="Base currency(AKA first pair)",
        max_length=20,
        help_text=(
            "The base currency is always the first cryptocurrency in a crypto trading pair."
            "The base currency is the base to which the other currency is compared – if we look at our EUR/USD"
            "example from earlier, euro (EUR) is the base currency. For BTC/USDT, BTC is the base currency."
            "The ticker before the “/” is always the base currency in crypto. Another example is ETH/BTC, "
            "in which ETH is the base currency."
        )
    )
    quote_currency = models.CharField(
        verbose_name="Quote currency(AKA second pair)",
        max_length=20,
        help_text=(
            "The second part is the quote currency."
            "It is the price of the base currency quoted using the quote currency."
            "The quote currency comes after the “/”. For the trading pair of BTC/USDT, USDT is the quote currency."
            "If we refer back to the EUR/USD example, the U.S. dollar (USD) is the quote currency."
        )
    )
    # save the unique futures symbol for this exchange
    futures_symbol = models.CharField(
        verbose_name="Futures symbol",
        max_length=32,
        blank=True,
    )
    market_type = models.CharField(
        choices=TradingSignalType.choices,
        verbose_name="Market type",
        max_length=10,
    )
    is_active = models.BooleanField(default=True)

    tick_size = models.FloatField(
        default=1.0,
        verbose_name="Tick Size"
    )

    # image  #TODO: relation with image model.

    class Meta:
        unique_together = ('exchange_name', 'coin_pair', 'market_type')

    def __str__(self) -> str:
        return f"{self.exchange_name}:{self.coin_pair}:{self.market_type}"


class SignalVirtualBalance(BaseModelClass):
    service = models.OneToOneField(
        to='services.service',
        related_name='virtual_value',
        on_delete=models.CASCADE,
        verbose_name='Service id',
        db_index=True
    )
    balance = models.FloatField(default=10000,
                                verbose_name="Balance")
    frozen = models.FloatField(default=0,
                               verbose_name="Frozen Balance")

    class Meta:
        verbose_name = 'Signal Virtual Balance'
        verbose_name_plural = 'Signal Virtual Balances'
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f"service {self.service.id} balance: {self.balance}"
    @property
    def available_balance(self):
        return self.balance - self.frozen