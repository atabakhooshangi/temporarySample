from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.base_model import BaseModelClass
from core.choice_field_types import (
    OrderSideChoices,
    OrderTypeChoices,
    TradingOrderStatusChoices,
    TradingOrderType, )


class TradingOrder(BaseModelClass):
    order_id = models.CharField(
        verbose_name='Order_Id',
        max_length=256,
        null=True,
        blank=True,
    )
    parent_order = models.ForeignKey(
        to='self',
        verbose_name='Parent order',
        related_name='copy_orders',
        related_query_name='copy_order',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    exchange_order_id = models.CharField(
        max_length=63,
        blank=True,
        # TODO : null=True
    )
    service = models.ForeignKey(
        verbose_name="Service",
        to="services.Service",
        related_name="service_orders",
        related_query_name="service_order",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    signal_ref = models.ForeignKey(
        verbose_name="signal reference",
        to='signals.TradingSignal',
        related_name='signal_orders',
        related_query_name='signal_order',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    profile = models.ForeignKey(
        verbose_name="Profile",
        to="user.Profile",
        related_name="orders",
        null=True,
        blank=True,
        related_query_name="order",
        on_delete=models.CASCADE
    )
    state = models.CharField(
        max_length=40,
        choices=TradingOrderStatusChoices.choices,
        default=TradingOrderStatusChoices.OPEN,
        verbose_name='State'
    )
    type = models.CharField(
        max_length=8,
        choices=TradingOrderType.choices,
        default=TradingOrderType.FUTURES,
        verbose_name='Type'
    )
    exchange = models.CharField(
        verbose_name="Exchange",
        max_length=32
    )
    coin_pair = models.CharField(
        verbose_name="Coin pair",
        max_length=32
    )
    # Symbol should send to ccxt for get order and position.
    symbol = models.CharField(
        verbose_name="Symbol",
        max_length=32,
        blank=True,
    )
    leverage = models.FloatField(
        verbose_name="Leverage",
        null=True,
        blank=True
    )
    order_type = models.CharField(
        verbose_name="Order type",
        choices=OrderTypeChoices.choices,
        default=OrderTypeChoices.LIMIT,
        max_length=32
    )
    side = models.CharField(
        verbose_name="Side",
        choices=OrderSideChoices.choices,
        default=OrderSideChoices.BUY,
        max_length=4,
    )
    # Keep the value based on USDT (Tether)
    # This variable represents the value obtained from the user, pegged to USDT.
    # TODO: change variable name to value, change in tpt-copy project also.
    amount = models.DecimalField(
        verbose_name="Amount",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    # Keep the value based on base currency like(ADA,ETH, ...)
    # This variable represents the value obtained from the exchange(size or cumExecQty), pegged to base currency.
    # NOTE : The maximum number of decimal places between Bybit and BigNX is 4. If a new exchange is added,
    # it may be necessary to change this value.
    quantity = models.DecimalField(
        verbose_name="Quantity",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    filled_amount = models.DecimalField(
        verbose_name="Filled amount",
        decimal_places=4,
        max_digits=14,
        null=True,
        blank=True,
        default=0
    )
    price = models.FloatField(
        verbose_name="Price",
        null=True,
        blank=True,
    )
    avg_price = models.DecimalField(
        verbose_name='Average Price',
        null=True,
        blank=True,
        decimal_places=6,
        max_digits=20
    )
    stop_price = models.FloatField(
        verbose_name="Stop price",
        null=True,
        blank=True,
    )
    entry_point = models.FloatField(
        verbose_name="Entry point",
        null=True,
        blank=True,
    )
    stop_loss = models.FloatField(
        verbose_name="Stop loss",
        null=True,
        blank=True,
    )
    take_profit = models.FloatField(
        verbose_name="Take profit",
        null=True,
        blank=True,
    )

    user_margin = models.FloatField(
        verbose_name="User margin",
        null=True,
        blank=True
    )
    user_take_profit_percentage = models.FloatField(
        verbose_name="Uesr take profit percentage",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    user_stop_loss_percentage = models.FloatField(
        verbose_name="User stop los percentage",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    closed_time = models.DateTimeField(
        verbose_name='Closed Time',
        null=True,
        blank=True
    )
    position = models.ForeignKey(
        to='Position',
        verbose_name='Position',
        related_name='trading_orders',
        related_query_name='trading_order',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    reduce_only = models.BooleanField(
        default=False,
    )
    submission_error = models.TextField(null=True, blank=True)
    api_key = models.ForeignKey(
        to='ApiKey',
        verbose_name='API_KEY',
        related_name='trading_orders_apis',
        related_query_name='trading_order_api',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @property
    def is_copy_trader_order(self):
        return self.parent_order is None

    @property
    def opposite_side(self):
        if self.side == OrderSideChoices.BUY:
            return OrderSideChoices.SELL
        else:
            return OrderSideChoices.BUY

    @property
    def position_volume(self):
        if not self.leverage or not self.amount:
            return
        return self.leverage * float(self.amount)

    class Meta:
        verbose_name = 'Trading Order'
        verbose_name_plural = 'Trading Order'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.id}"


class CopySetting(models.Model):
    profile = models.ForeignKey(
        verbose_name="Profile",
        to="user.Profile",
        related_name="copy_settings",
        related_query_name="copy_setting",
        on_delete=models.CASCADE,
    )
    service = models.ForeignKey(
        verbose_name="Service",
        to="services.Service",
        related_name="copy_settings",
        related_query_name="copy_setting",
        on_delete=models.CASCADE
    )
    margin = models.FloatField(
        verbose_name="Margin",
        default=2.0
    )
    take_profit_percentage = models.FloatField(
        verbose_name="Take profit percentage",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    stop_loss_percentage = models.FloatField(
        verbose_name="Stop loss percentage",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    is_active = models.BooleanField(
        verbose_name="Copy is active",
        default=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'service'],
                name='unique_setting_per_service_and_profile'
            )
        ]
