# Generated by Django 4.2 on 2023-12-24 11:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0042_add_virtual_value_to_every_services'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tradingsignal',
            name='percentage_of_fund',
            field=models.FloatField(default=100, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Percentage of fund'),
        ),
    ]
