# Generated by Django 3.2 on 2023-03-01 09:19

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0025_merge_20230227_0848'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='subscription_fee',
            field=models.IntegerField(blank=True, default=0, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Subscription fee'),
        ),
        migrations.AlterField(
            model_name='service',
            name='watch_list',
            field=models.JSONField(blank=True, default=list, null=True, verbose_name='Watch List'),
        ),
    ]