from core.base_model import BaseModelClass
from core.choice_field_types import ExchangeChoices
from django.db import models


class ApiKey(BaseModelClass):
    name = models.CharField(
        verbose_name='Name',
        max_length=256,
        null=True,
        blank=True
    )
    exchange = models.CharField(
        verbose_name='Exchange',
        choices=ExchangeChoices.choices,
        max_length=50
    )
    # Note: The token value equivalent for this field is correct in certain exchanges, such as Nobitex.
    api_key = models.CharField(
        verbose_name='API Key',
        max_length=256,
    )  # TODO: add encryption strategy

    secret_key = models.CharField(
        verbose_name='Secret Key',
        max_length=256,
        null=True,
        blank=True
    )  # TODO: add encryption strategy
    password = models.CharField(
        verbose_name='Password',
        max_length=30,
        blank=True
    )  # required for some exchanges
    owner = models.ForeignKey(
        verbose_name='Owner',
        to='user.Profile',
        related_name='api_keys',
        related_query_name='api_key',
        on_delete=models.CASCADE
    )
    is_default = models.BooleanField(
        verbose_name='Is Default',
        default=False,
    )

    # Todo: Add relation to service when subscribe.

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = 'api-key'
        verbose_name_plural = 'api-key'
        unique_together = (
            'exchange',
            'api_key',
            'secret_key'
        )
        ordering = ('-id',)


class ProfileServiceApiKey(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    api_key = models.ForeignKey(
        verbose_name='API Key',
        to='copytrading.ApiKey',
        related_name='profile_service_api_keys',
        related_query_name='profile_service_api_key',
        on_delete=models.CASCADE
    )
    service = models.ForeignKey(
        verbose_name='Service',
        to='services.Service',
        related_name='profile_service_api_keys',
        related_query_name='profile_service_api_key',
        on_delete=models.CASCADE
    )
    profile = models.ForeignKey(
        verbose_name='Profile',
        to='user.Profile',
        related_name='profile_service_api_keys',
        related_query_name='profile_service_api_key',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Profile Service Api Key'
        verbose_name_plural = 'Profile Service Api Keys'
        ordering = ('-id',)

    def __str__(self):
        return self.profile.username
