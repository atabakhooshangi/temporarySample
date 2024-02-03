# Generated by Django 3.2 on 2023-07-12 11:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0037_merge_0036_auto_20230627_1415_0036_signalservice'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='signalservice',
            options={'verbose_name': 'Service Rank'},
        ),
        migrations.AlterField(
            model_name='service',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='subscriptioninvoice',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]