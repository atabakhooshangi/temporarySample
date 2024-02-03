# Generated by Django 3.2 on 2023-07-31 12:56

from django.db import migrations, models

from signals.models import CoinDecimalNumber


class Migration(migrations.Migration):
    def forwards_func(apps, schema_editor):
        coin_pair_list = [
            ('USDT/BTC', 2),
            ('USDT/SHIB', 8),
            ('USDT/FTM', 4),
            ('USDT/MANA', 4),
            ('USDT/MATIC', 4),
            ('USDT/FIL', 3),
            ('USDT/BNB', 1),
            ('USDT/ATOM', 4),
            ('USDT/ADA', 4),
            ('USDT/UNI', 3),
            ('USDT/AAVE', 1),
            ('USDT/DOGE', 5),
            ('USDT/PAXG', 1),
            ('USDT/SOL', 2),
            ('USDT/AVAX', 2),
            ('USDT/ETH', 2),
            ('USDT/DYDX', 3),
            ('USDT/CRV', 4),
            ('USDT/LINK', 3),
            ('USDT/PEPE', 9),
            ('IRR/BTC', 1),
            ('IRR/SHIB', 3),
            ('IRR/FTM', 1),
            ('IRR/MANA', 1),
            ('IRR/MATIC', 1),
            ('IRR/FIL', 1),
            ('IRR/BNB', 1),
            ('IRR/ATOM', 1),
            ('IRR/ADA', 1),
            ('IRR/UNI', 1),
            ('IRR/AAVE', 1),
            ('IRR/DOGE', 1),
            ('IRR/PAXG', 1),
            ('IRR/SOL', 1),
            ('IRR/AVAX', 1),
            ('IRR/ETH', 1),
            ('IRR/LINK', 1),
            ('IRR/DYDX', 1),
            ('IRR/CRV', 1),
            ('IRR/PEPE', 9)
        ]
        for coin_pair in coin_pair_list:
            if CoinDecimalNumber.objects.filter(coin_pair=coin_pair[0]).exists():
                CoinDecimalNumber.objects.filter(coin_pair=coin_pair[0]).update(decimal_num=coin_pair[1])
            else:
                CoinDecimalNumber.objects.create(coin_pair=coin_pair[0], decimal_num=coin_pair[1])

    dependencies = [
        ('signals', '0026_coin_decimal_generate_data'),
    ]

    operations = [
        migrations.RunPython(code=forwards_func, reverse_code=migrations.RunPython.noop)
    ]