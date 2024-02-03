from django.db import models
from django.utils import timezone

from core.base_model import BaseModelClass
from django.contrib.postgres.fields import ArrayField

from core.message_text import MessageText
from services.utils import get_wallex_usdt_to_toman_price


class AssignorTypeChoices(models.TextChoices):
    ADMIN_LEVEL = 'admin_level', 'admin_level'
    USER_LEVEL = 'user_level', 'user_level'
    SERVICE_LEVEL = 'service_level', 'service_level'


class InvitationTypeChoices(models.TextChoices):
    PERCENTAGE_DISCOUNT = 'percentage_discount', 'percentage_discount'
    FIXED_DISCOUNT = 'fixed_discount', 'fixed_discount'
    FIXED_ADDITION = 'fixed_addition', 'fixed_addition'


class InvitationCode(BaseModelClass):
    owner_id = models.PositiveBigIntegerField(
        verbose_name="owner id",
    )
    assignor_type = models.CharField(
        verbose_name='Assignor type',
        max_length=128,
        choices=AssignorTypeChoices.choices
    )
    invitation_type = models.CharField(
        verbose_name='Invitation type',
        max_length=128,
        choices=InvitationTypeChoices.choices
    )
    invitation_amount = models.PositiveIntegerField(
        verbose_name='Invitation amount',
    )
    code_string = models.SlugField(
        verbose_name='Code',
        max_length=512,
        unique=True,
    )  # NOTE: it might be better to add ADMIN prefix for admin codes
    description = models.TextField(
        verbose_name='Description',
        null=True,
        blank=True
    )
    only_assignor = models.BooleanField(
        verbose_name='Only assignor',
    )
    user_limit = models.PositiveIntegerField(
        verbose_name='User limit',
    )
    used_count = models.PositiveIntegerField(
        verbose_name='Used count',
        default=0
    )
    start_date = models.DateTimeField(
        verbose_name='Start date',
        null=True,
        blank=True
    )
    expire_date = models.DateTimeField(
        verbose_name='Expire date',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.code_string

    def rounding_final_price(self, amount) -> (float, bool):
        # rounding to half
        if amount == int(amount):
            return amount
        if amount <= int(amount) + 0.5:
            return int(amount) + 0.5
        else:
            return round(amount)

    def calculate_final_price(self, service, do_irt_calculate=False) -> (float, bool):
        successful_calculation = False
        message = "ok"
        if do_irt_calculate:
            usdt_price = get_wallex_usdt_to_toman_price() * 10
        else:
            usdt_price = 0
        subscription_fee = service.subscription_fee  # irt_amount or service.subscription_fee
        final_amount = subscription_fee
        irt_final_amount = int(subscription_fee * usdt_price)
        if subscription_fee == 0:
            message = "service is free"
            return successful_calculation, message, final_amount, irt_final_amount

        if self.user_limit != 0 and self.used_count >= self.user_limit:
            message = MessageText.InvitationCodeIsExpired400
            return successful_calculation, message, final_amount, irt_final_amount

        if self.expire_date and self.expire_date < timezone.now():
            message = MessageText.InvitationCodeIsExpired400
            return successful_calculation, message, final_amount, irt_final_amount
        elif self.start_date and self.start_date > timezone.now():
            message = MessageText.InvitationIsNotStarted400
            return successful_calculation, message, final_amount, irt_final_amount

        assignee_ids = self.assignee_entities.first().assignee_id
        if assignee_ids:
            if assignee_ids != [0] and service.id not in assignee_ids:
                message = MessageText.WrongCodeForThisService400
                return successful_calculation, message, final_amount, irt_final_amount
        else:
            message = MessageText.WrongCodeForThisService400
            return successful_calculation, message, subscription_fee, int(subscription_fee * usdt_price)
        if self.invitation_type == InvitationTypeChoices.PERCENTAGE_DISCOUNT:
            successful_calculation = True
            final_amount = (subscription_fee - (subscription_fee * self.invitation_amount / 100))
            final_amount = self.rounding_final_price(final_amount)
            irt_final_amount = int(final_amount * usdt_price)
            return successful_calculation, message, final_amount, irt_final_amount
        elif self.invitation_type == InvitationTypeChoices.FIXED_DISCOUNT:
            successful_calculation = True
            final_amount = subscription_fee - self.invitation_amount
            final_amount = self.rounding_final_price(final_amount)
            irt_final_amount = int(final_amount * usdt_price)
            return successful_calculation, message, final_amount, irt_final_amount
        elif self.invitation_type == InvitationTypeChoices.FIXED_ADDITION:
            pass
        # TODO: this is for future to add fixed addition into owner balance
        # irt_subscription_fee =
        return successful_calculation, message, subscription_fee, int(subscription_fee * usdt_price)


class AssigneeEntities(BaseModelClass):
    invitation = models.ForeignKey(
        verbose_name='Invitation code',
        to='invitation.InvitationCode',
        related_name='assignee_entities',
        on_delete=models.CASCADE
    )
    assignee_id = ArrayField(
        verbose_name='Assignees id',  # if this is zero, it will affect all services or all users
        base_field=models.IntegerField(),
    )

    def __str__(self):
        return f"{self.invitation.code_string} - {self.assignee_id}"


class InvitationCodeUsage(BaseModelClass):
    invitation_code = models.ForeignKey(
        verbose_name='Invitation code',
        to='invitation.InvitationCode',
        related_name='invitation_code_usages',
        on_delete=models.PROTECT
    )
    service = models.ForeignKey(
        verbose_name='Service',
        to='services.Service',
        related_name='service_invitation_code_usages',
        on_delete=models.PROTECT
    )
    user = models.ForeignKey(
        verbose_name='User',
        to='user.Profile',
        on_delete=models.PROTECT,
        related_name='user_invitation_code_usages',
    )
    subscription = models.ForeignKey(
        verbose_name='Subscription',
        to='services.Subscription',
        related_name='subscription_invitation_code_usages',
        on_delete=models.PROTECT
    )

    def __str__(self):
        return f"{self.invitation_code.code_string} - {self.service.title} - {self.user.username}"


class InvitationReferral(BaseModelClass):
    owner_id = models.PositiveBigIntegerField(
        verbose_name="owner id",
    )
    referral_code = models.TextField(
        verbose_name='Referral code',
    )
    invitation_code = models.ForeignKey(
        verbose_name='Invitation code',
        to='invitation.InvitationCode',
        related_name='invitation_code_invitation_referrals',
        on_delete=models.PROTECT
    )
    seen = models.BooleanField(
        verbose_name='Seen',
        default=False
    )

    class Meta:
        unique_together = ['owner_id', 'referral_code']

    def __str__(self):
        return f"{self.invitation_code.code_string} - {self.owner_id}"
