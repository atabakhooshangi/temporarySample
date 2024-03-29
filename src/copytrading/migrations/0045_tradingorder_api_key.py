# Generated by Django 3.2 on 2023-10-08 11:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0044_alter_tradingorder_signal_ref'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingorder',
            name='api_key',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trading_orders_apis', related_query_name='trading_order_api', to='copytrading.apikey', verbose_name='API_KEY'),
        ),
    ]
