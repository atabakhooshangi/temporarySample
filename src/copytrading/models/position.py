import decimal

from django.db import models

from core.base_model import BaseModelClass
from core.choice_field_types import PositionSideChoice, PositionStatusChoices


class Position(BaseModelClass):
    profile = models.ForeignKey(
        verbose_name="Profile",
        to="user.Profile",
        related_name="positions",
        related_query_name="position",
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    # Set for some exchange like Nobitex
    exchange_position_id = models.IntegerField(
        verbose_name='Exchange PositionId',
        null=True,
        blank=True
    )
    # Keep the value based on USDT (Tether)
    # This variable represents the value obtained from the user, pegged to USDT.
    amount = models.DecimalField(
        verbose_name="Amount",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    # Keep the value based on USDT (Tether)
    # This variable represents the value obtained from the exchange(cumExecValue or PositionValue), pegged to USDT.
    value = models.DecimalField(
        verbose_name="Value",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    # Keep the value based on base currency like(ADA,ETH, ...)
    # This variable represents the value obtained from the exchange(size or cumExecQty), pegged to base currency.
    quantity = models.DecimalField(
        verbose_name="Quantity",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    symbol = models.CharField(
        verbose_name="Symbol",
        max_length=32,
        blank=True,
    )
    side = models.CharField(
        verbose_name="Side",
        max_length=10,
        choices=PositionSideChoice.choices,
        blank=True,
        null=True
    )
    status = models.CharField(
        verbose_name='Status',
        max_length=20,
        choices=PositionStatusChoices.choices,
        default=PositionStatusChoices.OPEN,
        blank=True
    )
    leverage = models.FloatField(
        verbose_name="Leverage",
        null=True,
        blank=True
    )
    closed_pnl = models.DecimalField(
        verbose_name='Closed Pnl',
        decimal_places=4,
        max_digits=15,
        default=0.0000
    )
    closed_pnl_percentage = models.DecimalField(
        verbose_name='Closed pnl percentage',
        decimal_places=2,
        max_digits=5,
        default=0.0000,
        blank=True
    )
    unrealised_pnl = models.DecimalField(
        verbose_name='Unrealised Pnl',
        decimal_places=4,
        max_digits=14,
        null=True,
        blank=True
    )
    avg_entry_price = models.DecimalField(
        verbose_name='Avg Entry Price',
        decimal_places=4,
        max_digits=20,
        null=True,
        blank=True
    )
    avg_exit_price = models.DecimalField(
        verbose_name="Avg Exit point",
        decimal_places=4,
        max_digits=20,
        null=True,
        blank=True
    )
    closed_datetime = models.DateTimeField(
        verbose_name='Closed DateTime',
        blank=True,
        null=True
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
    liquidation_price = models.DecimalField(
        verbose_name="Liquidation Price",
        decimal_places=2,
        max_digits=14,
        null=True,
        blank=True
    )
    service = models.ForeignKey(
        verbose_name='Service',
        to='services.service',
        on_delete=models.CASCADE,
        related_name='position_services',
        related_query_name='position_service',
        blank=True,
        null=True
    )
    exchange_name = models.CharField(
        verbose_name="Exchange",
        max_length=32,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Position'
        verbose_name_plural = 'Positions'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.profile.title}'s  {self.symbol} position with id : {self.id}"

    @property
    def closed_pnl_percentage_calc(self):
        return round((self.unrealised_pnl / ((self.amount * self.avg_entry_price) / decimal.Decimal(self.leverage))) * 100, 2)

    def update_model_instance(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.save()
