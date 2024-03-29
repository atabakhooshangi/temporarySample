# Generated by Django 3.2 on 2023-07-22 13:50

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0038_alter_tradingorder_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apikey',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='position',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='tradingorder',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
