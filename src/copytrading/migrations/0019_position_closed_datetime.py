# Generated by Django 3.2 on 2023-05-14 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0018_auto_20230514_1057'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='closed_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Closed DateTime'),
        ),
    ]
