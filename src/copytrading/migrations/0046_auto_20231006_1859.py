# Generated by Django 3.2 on 2023-10-06 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0045_merge_20231001_0900'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profileserviceapikey',
            options={'ordering': ('-id',), 'verbose_name': 'Profile Service Api Key', 'verbose_name_plural': 'Profile Service Api Keys'},
        ),
        migrations.AlterField(
            model_name='position',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True, verbose_name='Amount'),
        ),
        migrations.AlterField(
            model_name='tradingorder',
            name='state',
            field=models.CharField(choices=[('New', 'New'), ('Active', 'Active'), ('PartiallyFilled', 'Partially Filled'), ('PartiallyFilledCanceled', 'Partially Filled Canceled'), ('FILLED', 'Filled'), ('Cancelled', 'Cancelled'), ('Triggered', 'Triggered'), ('open', 'Open'), ('closed', 'Closed'), ('failed', 'Failed'), ('x_open', 'X Open'), ('OpposeSideMarketClose', 'Oppose Side Market Close')], default='open', max_length=40, verbose_name='State'),
        ),
    ]
