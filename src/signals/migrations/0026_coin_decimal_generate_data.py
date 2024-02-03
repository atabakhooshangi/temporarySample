# Generated by Django 3.2 on 2023-07-31 12:56

from django.db import migrations, models

from signals.models import CoinDecimalNumber


class Migration(migrations.Migration):
    def forwards_func(apps, schema_editor):
        coin_pair_list = [
            ('USDT/BTC', 100),
            ('USDT/SHIB', 100000000),
            ('USDT/FTM', 10000),
            ('USDT/MANA', 10000),
            ('USDT/MATIC', 10000),
            ('USDT/FIL', 1000),
            ('USDT/BNB', 10),
            ('USDT/ATOM', 10000),
            ('USDT/ADA', 10000),
            ('USDT/UNI', 1000),
            ('USDT/AAVE', 10),
            ('USDT/DOGE', 100000),
            ('USDT/PAXG', 1),
            ('USDT/SOL', 100),
            ('USDT/AVAX', 100),
            ('USDT/ETH', 100),
            ('USDT/DYDX', 1000),
            ('USDT/CRV', 10000),
            ('USDT/LINK', 1000),
            ('USDT/PEPE', 1000000000),
            ('IRR/BTC', 1),
            ('IRR/SHIB', 1000),
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
            ('IRR/PEPE', 1000000000)
        ]
        object_list = list()
        for coin_pair in coin_pair_list:
            if not CoinDecimalNumber.objects.filter(coin_pair=coin_pair[0]).exists():
                object_list.append(CoinDecimalNumber(
                    coin_pair=coin_pair[0], decimal_num=coin_pair[1]
                ))
        CoinDecimalNumber.objects.bulk_create(object_list)

    dependencies = [
        ('signals', '0025_coindecimalnumber'),
    ]

    operations = [
        migrations.RunPython(code=forwards_func, reverse_code=migrations.RunPython.noop)
    ]
