# Generated by Django 3.2 on 2023-05-21 18:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0025_merge_20230521_1212'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='avg_exit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Avg Exit point'),
        ),
    ]