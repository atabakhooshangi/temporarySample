import django.utils.timezone
from django.db import models

from core.base_model import BaseModelClass


# Create your models here.
class Campaign(BaseModelClass):
    campaign_key = models.SlugField(
        verbose_name="Campaign key",
        max_length=512,
        unique=True,
    )
    campaign_name = models.TextField(
        verbose_name="Campaign name"
    )
    campaign_name_fa = models.TextField(
        verbose_name="Campaign name FA"
    )
    campaign_description = models.TextField(
        verbose_name="Campaign description"
    )
    campaign_description_fa = models.TextField(
        verbose_name="Campaign description FA"
    )
    start_date = models.DateTimeField(
        verbose_name="Start time",
        default=django.utils.timezone.now
    )
    end_date = models.DateTimeField(
        verbose_name="End time",
        default=django.utils.timezone.now
    )
    show = models.BooleanField(
        verbose_name="Show",
    )

    def __str__(self):
        return self.campaign_name
