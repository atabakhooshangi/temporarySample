# Generated by Django 3.2 on 2023-01-30 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0013_alter_tradingsignal_sid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tradingsignal',
            name='entry_point',
            field=models.BigIntegerField(default=0, verbose_name='Entry point'),
        ),
    ]
