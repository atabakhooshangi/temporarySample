# Generated by Django 3.2 on 2023-05-15 12:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0019_position_closed_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='leverage',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Leverage'),
        )
    ]
