from datetime import datetime

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.functional import cached_property

from core.base_model import BaseModelClass
from core.choice_field_types import (
    ServiceTypeChoices,
    CoinChoices,
    ServiceStateChoices,
    CopyExchangeChoices
)
from services.utils import get_wallex_usdt_to_toman_price


class Service(BaseModelClass):
    title = models.CharField(
        verbose_name="Title",
        max_length=64,
        blank=True
    )
    link = models.URLField(
        verbose_name="Link",
        blank=True
    )
    description = models.TextField(
        verbose_name="Description",
        blank=True
    )
    image = models.ForeignKey(
        to="media.Media",
        verbose_name="Image",
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )
    service_type = models.CharField(
        verbose_name="Service type",
        max_length=16,
        choices=ServiceTypeChoices.choices,
        default=ServiceTypeChoices.SIGNAL,
        db_index=True
    )
    profile = models.ForeignKey(
        to="user.Profile",
        verbose_name="Profile",
        blank=True,
        null=True,
        related_name='services',
        related_query_name='services',
        on_delete=models.CASCADE
    )
    coin = models.CharField(
        verbose_name="Coin",
        max_length=16,
        choices=CoinChoices.choices,
    )
    is_visible = models.BooleanField(
        verbose_name="Is visible",
        default=True,
        db_index=True
    )
    subscription_fee = models.IntegerField(
        verbose_name="Subscription fee",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        default=0
    )
    platform_fee = models.IntegerField(
        verbose_name="Platform fee",
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        default=settings.PLATFORM_DEFAULT_FEE
    )
    subscription_coin = models.CharField(
        verbose_name="Subscription coin",
        max_length=16,
        choices=CoinChoices.choices,
    )
    state = models.CharField(
        verbose_name='State',
        max_length=50,
        choices=ServiceStateChoices.choices,
        default=ServiceStateChoices.TRACKING,
    )
    exchanges = models.JSONField(
        verbose_name='Exchange',
        default=list,
        null=True,
        blank=True
    )
    copy_exchange = models.CharField(
        max_length=16,
        verbose_name="Copy exchange",
        choices=CopyExchangeChoices.choices,
        blank=True,
    )
    watch_list = models.JSONField(
        verbose_name='Watch List',
        default=list,
        null=True,
        blank=True
    )
    has_trial = models.BooleanField(
        default=True
    )
    balance = models.DecimalField(
        verbose_name='Balance',
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True
    )
    # NOTE: persisting calculated data in service 
    # table for reducing query bottleneck(maybe move
    # them to json data type later for reducing the 
    # number of columns or keep them for querying purpose)
    draw_down = models.JSONField(
        verbose_name='Draw Down',
        default=dict,
        null=True,
        blank=True
    )
    initial_draw_down = models.JSONField(
        verbose_name='Initial Draw Down',
        default=dict,
        null=True,
        blank=True
    )
    history_used = models.BooleanField(
        verbose_name="History Used",
        default=False
    )


    @property
    def vip_member_count(self):
        return self.subscriptions.filter(
            expire_time__gt=datetime.now(),
            is_paid=True,
        ).order_by().distinct('subscriber_id').count()

    @cached_property
    def irt_subscription_price(self):
        if self.subscription_fee is None:
            return 0

        if self.subscription_coin == CoinChoices.USDT:
            return get_wallex_usdt_to_toman_price() * self.subscription_fee
        return self.subscription_fee

    @property
    def is_free(self):
        if self.subscription_fee == 0:
            return True
        return False

    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['-id']

    def __str__(self) -> str:
        return f"{self.title} - {self.id}"


class SignalService(Service):
    class Meta:
        verbose_name = 'Service Rank'
        proxy = True
