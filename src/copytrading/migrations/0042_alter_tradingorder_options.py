# Generated by Django 3.2 on 2023-08-27 09:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0041_auto_20230809_0731'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tradingorder',
            options={'ordering': ['-created_at'], 'verbose_name': 'Trading Order', 'verbose_name_plural': 'Trading Order'},
        ),
    ]