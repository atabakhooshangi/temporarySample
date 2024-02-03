# Generated by Django 3.2 on 2023-05-16 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0019_position_closed_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True, verbose_name='Amount'),
        ),
        migrations.AddField(
            model_name='position',
            name='symbol',
            field=models.CharField(blank=True, max_length=32, verbose_name='Symbol'),
        ),
        migrations.AlterField(
            model_name='tradingorder',
            name='amount',
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True, verbose_name='Amount'),
        ),
    ]