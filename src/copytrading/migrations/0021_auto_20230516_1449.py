# Generated by Django 3.2 on 2023-05-16 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0020_auto_20230516_1415'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='status',
            field=models.CharField(blank=True, choices=[('OPEN', 'Open'), ('CLOSED', 'Closed'), ('CANCELED', 'Canceled')], default='OPEN', max_length=20, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='tradingorder',
            name='state',
            field=models.CharField(choices=[('New', 'New'), ('Active', 'Active'), ('PartiallyFilled', 'Partially Filled'), ('PartiallyFilledCanceled', 'Partially Filled Canceled'), ('Filled', 'Filled'), ('Cancelled', 'Cancelled'), ('Triggered', 'Triggered'), ('open', 'Open'), ('closed', 'Closed')], default='open', max_length=40, verbose_name='State'),
        ),
    ]
