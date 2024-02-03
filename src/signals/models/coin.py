from django.db import models


class CoinDecimalNumber(models.Model):
    coin_pair = models.CharField(
        verbose_name='Coin name',
        max_length=256,
        unique=True
    )
    decimal_num = models.IntegerField(
        verbose_name='Decimal Num',
        help_text='Number of decimal for each coin pair'
    )

    class Meta:
        verbose_name = 'Coin Decimal Number'
        verbose_name_plural = 'Coin Decimal Number'
        ordering = ['coin_pair']

    def __str__(self):
        return f'{self.coin_pair}:{self.decimal_num}'
