# Generated by Django 3.2 on 2023-05-22 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0026_alter_position_avg_exit_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='copysetting',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Copy is active'),
        ),
    ]
