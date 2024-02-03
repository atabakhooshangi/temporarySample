from django.db import models

from core.choice_field_types import HistoryTypeChoices


class DailyAggregatedPnl(models.Model):
    service = models.ForeignKey(
        to='services.Service',
        verbose_name='Service',
        related_name='daily_aggregated_pnls',
        related_query_name='daily_aggregated_pnl',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        db_index=True
    )
    percentage = models.FloatField(
        verbose_name="Percentage",
        null=False,
        blank=False
    )
    amount = models.FloatField(
        verbose_name="Amount",
        null=False,
        blank=False,
        db_index=True
    )
    v_balance=models.FloatField(
        verbose_name="Virtual Balance",
        default=0.0
    )
    v_balance_change = models.FloatField(
        verbose_name="Virtual Balance Change",
        default=0.0
    )
    date = models.DateField(
        verbose_name="Date",
        null=False,
        blank=False,
        db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['date', 'service'],
                name='unique_aggregated_pnl_per_date_and_service'
            )
        ]


# Return of Investment
class DailyROI(models.Model):
    percentage = models.FloatField(
        verbose_name="Percentage",
        null=False,
        blank=False
    )
    amount = models.FloatField(
        verbose_name="Amount",
        null=False,
        blank=False,
        default=0
    )

    roi_history = models.ForeignKey(
        to="ROIHistory",
        related_name="rois",
        related_query_name="roi",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        db_index=True
    )
    number = models.PositiveSmallIntegerField(
        null=False,
        blank=False
    )
    date = models.DateField(
        verbose_name="Date",
        null=False,
        blank=False
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['roi_history', 'number'],
                name='unique_roi_history_per_number'
            )
        ]


class ROIHistory(models.Model):
    service = models.ForeignKey(
        to='services.Service',
        verbose_name='Service',
        related_name='roi_history_services',
        related_query_name='roi_history_service',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )
    history_type = models.CharField(
        verbose_name="History type",
        choices=HistoryTypeChoices.choices,
        max_length=16
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'history_type'],
                name='unique_history_type_per_service'
            )
        ]