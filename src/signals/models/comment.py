from django.db import models

from core.base_model import BaseModelClass


class Comment(BaseModelClass):
    author = models.ForeignKey(
        to='user.Profile',
        verbose_name='Author',
        related_name='authors',
        related_query_name='authors',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )
    trading_signal = models.ForeignKey(
        to='TradingSignal',
        verbose_name='Trading signal',
        related_name='comments',
        related_query_name='comments',
        on_delete=models.CASCADE,
        null=True
    )
    parent = models.ForeignKey(
        to='self',
        verbose_name='Parent',
        related_name='replies',
        related_query_name='replies',
        on_delete=models.CASCADE,
        null=True
    )

    comment = models.TextField(
        verbose_name='comment',
        blank=True
    )

    def children(self):
        return Comment.objects.filter(parent=self)

    @property
    def is_parent(self):
        if self.parent is not None:
            return False
        return True

    class Meta:
        verbose_name = 'comment'
        verbose_name_plural = 'comments'
        ordering = ('created_at',)

    def __str__(self):
        return self.comment
