from django.db import models
from core.base_model import BaseModelClass


class InviteBonus(BaseModelClass):
    subscriber_iam_id = models.PositiveIntegerField(null=False, blank=False, unique=True)
    inviter_id = models.IntegerField(null=True, blank=True)
    inviter_referral_code = models.CharField(max_length=30, null=True, blank=True)
    amount = models.FloatField(default=0, null=True, blank=True)
    additional_data = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        verbose_name = 'Invite Bonus'
        verbose_name_plural = 'Invite Bonuses'
        ordering = ['-created_at']

    def __str__(self):
        return f"subscriber---{self.subscriber_iam_id}"
