# Generated by Django 3.2 on 2023-05-03 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0006_auto_20230503_0816'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingorder',
            name='order_id',
            field=models.CharField(blank=True, max_length=256, null=True, verbose_name='Order_Id'),
        ),
        migrations.AlterField(
            model_name='position',
            name='position',
            field=models.CharField(blank=True, choices=[('LONG', 'long'), ('SHORT', 'short')], max_length=8, verbose_name='Position'),
        ),
    ]