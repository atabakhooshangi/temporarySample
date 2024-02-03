import json
import uuid
from datetime import datetime, timedelta
from typing import Tuple

from django.conf import settings
from django.db import models
from django_redis import get_redis_connection

from core.base_exception import DataNotExistException
from core.base_model import BaseModelClass, BaseModelManager
from core.choice_field_types import (
    SubscriptionInvoiceStatusChoices,
    SubscriptionPaymentTypeChoices,
)
from services.exceptions import UseSeriveTrialLimiteException, \
    UseThisServiceTrialException
from services.models import Service
from user.models import Profile


class SubscriptionFactoryManager(BaseModelManager):

    def get_or_create_trial(
            self,
            service: Service,
            subscriber: Profile,
            **fields
    ):

        subscriptions = Subscription.objects.filter(
            subscriber=subscriber,
            payment_type=SubscriptionPaymentTypeChoices.TRIAL
        )
        with get_redis_connection(alias='data_cache') as cache:
            setting = cache.get('setting')
            if not setting:
                raise DataNotExistException
            else:
                trial_limitation = json.loads(setting).get('trial_limitation')
            if subscriptions.count() < trial_limitation and (
                    service.id not in subscriptions.values('service_id').distinct().values_list('service_id',
                                                                                                flat=True)):
                start_time, end_time = Subscription.objects.new_subscription_datetimes(
                    service_id=service.id,
                    subscriber_id=subscriber.id,
                    subscription_duration=settings.TRIAL_SUBSCRIPTION_DURATION
                )
                trial_subscription = Subscription.objects.create(
                    service=service,
                    subscriber=subscriber,
                    payment_type=SubscriptionPaymentTypeChoices.TRIAL,
                    start_time=start_time,
                    expire_time=end_time,
                    is_paid=True,
                    **fields
                )
                return trial_subscription
            elif subscriptions.count() < trial_limitation:
                raise UseSeriveTrialLimiteException
            else:
                raise UseThisServiceTrialException

    def create_paid(
            self,
            service: Service,
            subscriber: Profile,
            **fields,
    ):
        return Subscription.objects.create(
            service=service,
            subscriber=subscriber,
            is_paid=True,
            **fields
        )

    def create_unpaid(
            self,
            service: Service,
            subscriber: Profile,
            **fields,
    ):
        return Subscription.objects.create(
            service=service,
            subscriber=subscriber,
            **fields,
        )


class SubscriptionManager(BaseModelManager):

    def active_subscription_exists(
            self,
            profile_id: int,
            service_id: int
    ):
        return Subscription.objects.filter(
            expire_time__gte=datetime.now(),
            subscriber_id=profile_id,
            service_id=service_id,
            is_paid=True,
        ).exists()

    def new_subscription_datetimes(
            self,
            service_id: int,
            subscriber_id: int,
            subscription_duration=settings.SUBSCRIPTION_DURATION,
    ) -> Tuple[datetime, datetime]:
        latest_subscription: Subscription = Subscription.objects.filter(
            service_id=service_id,
            subscriber_id=subscriber_id,
            expire_time__gte=datetime.now(),
            is_paid=True
        ).order_by('-expire_time').first()
        if latest_subscription:
            start_time = latest_subscription.expire_time
        else:
            start_time = datetime.now()

        expire_time = start_time + timedelta(
            days=subscription_duration
        )
        return start_time, expire_time

    def get_pending_subscription(
            self,
            service_id: int,
            subscriber_id: int,
    ):
        return Subscription.objects.filter(
            service_id=service_id,
            subscriber_id=subscriber_id,
            is_paid=False,
            start_time__isnull=True,
            expire_time__isnull=True,
        ).first()


class Subscription(BaseModelClass):
    service = models.ForeignKey(
        verbose_name="Service",
        to="services.Service",
        null=False,
        blank=False,
        related_name="subscriptions",
        related_query_name="subscription",
        on_delete=models.PROTECT
    )
    payment_type = models.CharField(
        verbose_name="Payment type",
        max_length=64,
        choices=SubscriptionPaymentTypeChoices.choices,
        blank=False
    )
    tracking_code = models.UUIDField(
        verbose_name="Tracking code",
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    previous_amount = models.FloatField(
        verbose_name="Previous amount before discount",
        null=True,
        blank=True
    )
    invitation_code = models.ForeignKey(
        verbose_name="Invitation code",
        to='invitation.InvitationCode',
        related_name='subscription_invoices',
        related_query_name='subscription_invoice',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    amount = models.FloatField(
        null=True,
        blank=True
    )
    discount_applied = models.BooleanField(
        verbose_name="Discount applied",
        default=False
    )
    subscriber = models.ForeignKey(
        verbose_name="Subscriber",
        to='user.Profile',
        null=False,
        blank=False,
        related_name='subscriptions',
        related_query_name='subscription',
        on_delete=models.PROTECT
    )
    start_time = models.DateTimeField(
        verbose_name="Start time",
        null=True,
        blank=True,
    )
    expire_time = models.DateTimeField(
        verbose_name="Expire time",
        null=True,
        blank=True,
    )
    is_paid = models.BooleanField(
        verbose_name="Is paid",
        default=False
    )
    factory = SubscriptionFactoryManager()
    objects = SubscriptionManager()

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-expire_time']

    def __str__(self) -> str:
        return f"Subscription for {self.subscriber.title} for service {self.service.title or self.service.service_type}"


class SubscriptionInvoice(BaseModelClass):
    ipg_track_id = models.CharField(
        verbose_name="IPG track id",
        max_length=128,
        null=True,
        blank=True,
        help_text=("Tracking code or reference id of the"
                   "internet payment gateway for this invoice")
    )  # track id for payment url of ipg
    profile = models.ForeignKey(
        verbose_name="Profile",
        to='user.Profile',
        related_name="subscription_invoices",
        related_query_name="subscription_invoice",
        on_delete=models.PROTECT
    )
    subscription = models.ForeignKey(
        verbose_name="Subscription",
        to='services.Subscription',
        related_name='invoices',
        related_query_name='invoice',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    previous_usdt_amount = models.FloatField(
        verbose_name="Previous USDT amount before discount",
        null=True,
        blank=True
    )
    previous_amount = models.FloatField(
        verbose_name="Previous amount before discount",
        null=True,
        blank=True
    )
    usdt_amount = models.FloatField(
        verbose_name="USDT amount",
        null=False,
        blank=False
    )
    amount = models.FloatField(
        verbose_name="Amount",
        null=False,
        blank=False
    )
    description = models.TextField(
        verbose_name="Description",
        blank=True
    )
    reference_id = models.CharField(
        verbose_name="Reference id",
        max_length=128,
        null=True,
        blank=True
    )
    additional_data = models.JSONField(
        verbose_name="Additional data",
        null=True,
        default=dict
    )
    status = models.CharField(
        verbose_name="Status",
        max_length=16,
        blank=False,
        choices=SubscriptionInvoiceStatusChoices.choices,
        default=SubscriptionInvoiceStatusChoices.PENDING,
    )

    def __str__(self):
        return f"{self.id} - {self.ipg_track_id}"

    def irt_amount(self):
        return int(self.amount / 10)
