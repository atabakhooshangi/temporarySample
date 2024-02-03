from django.db import models
from django.apps import apps
from core.base_model import BaseModelClass
from core.choice_field_types import ProfileStateChoices, ServiceTypeChoices


class Profile(BaseModelClass):
    owner_id = models.PositiveIntegerField(
        verbose_name="Owner id",
        null=False,
        blank=False,
        unique=True
    )
    title = models.CharField(
        verbose_name="Title",
        max_length=100,
        blank=False
    )
    username = models.CharField(
        verbose_name="Username",
        max_length=100,
        blank=False
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
    is_vendor = models.BooleanField(
        verbose_name="Is vendor",
        default=False
    )
    state = models.CharField(
        verbose_name="State",
        max_length=16,
        choices=ProfileStateChoices.choices,
        default=ProfileStateChoices.PUBLISH
    )
    instagram_id = models.CharField(
        verbose_name="Instagram id",
        max_length=24,
        blank=True
    )
    telegram_id = models.CharField(
        verbose_name="Telegram id",
        max_length=24,
        blank=True
    )
    twitter_id = models.CharField(
        verbose_name="Twitter id",
        max_length=24,
        blank=True
    )
    youtube_id = models.CharField(
        verbose_name="Youtube id",
        max_length=24,
        blank=True
    )
    trading_view_id = models.CharField(
        verbose_name="Trading view id",
        max_length=24,
        blank=True
    )
    default_name = models.BooleanField(
        default=False
    )
    follower_num = models.IntegerField(
        verbose_name='Follower num',
        default=0
    )
    following_num = models.IntegerField(
        verbose_name='Following num',
        default=0
    )
    subscriber_num = models.IntegerField(
        verbose_name='Subscriber num',
        default=0
    )
    subscription_num = models.IntegerField(
        verbose_name='Subscription num',
        default=0
    )
    quick_signal = models.BooleanField(
        verbose_name='Quick Signal',
        default=False,
    )

    @property
    def is_copy_vendor(self):
        return self.services.filter(service_type=ServiceTypeChoices.COPY).exists()

    @property
    def is_signal_vendor(self):
        return self.services.filter(service_type=ServiceTypeChoices.SIGNAL).exists()

    def has_subscription(self, service_id: int):
        Subscription = apps.get_model(app_label='services', model_name='Subscription')
        return Subscription.objects.active_subscription_exists(
            profile_id=self.id,
            service_id=service_id,
        )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.username} - (id:{self.id})"


class VendorProfileAnalytic(models.Model):
    profile = models.OneToOneField(
        verbose_name="Profile",
        to="user.Profile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    analytics = models.JSONField(default=dict)
