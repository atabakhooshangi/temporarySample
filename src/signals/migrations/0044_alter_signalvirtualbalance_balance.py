# Generated by Django 4.2 on 2024-01-01 05:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0043_alter_tradingsignal_percentage_of_fund'),
    ]

    operations = [
        migrations.AlterField(
            model_name='signalvirtualbalance',
            name='balance',
            field=models.FloatField(default=10000, verbose_name='Balance'),
        ),
    ]