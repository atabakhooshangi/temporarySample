# Generated by Django 3.2 on 2023-04-03 08:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_iamadmin'),
        ('services', '0028_auto_20230403_0832'),
        ('copytrading', '0002_apikey'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='copytradingorder',
            name='amount',
        ),
        migrations.RemoveField(
            model_name='copytradingorder',
            name='coin_pair',
        ),
        migrations.RemoveField(
            model_name='copytradingorder',
            name='order_type',
        ),
        migrations.RemoveField(
            model_name='copytradingorder',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='copytradingorder',
            name='price',
        ),
        migrations.RemoveField(
            model_name='copytradingorder',
            name='side',
        ),
        migrations.AlterField(
            model_name='copytradingorder',
            name='profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='copy_trading_orders', related_query_name='copy_trading_order', to='user.profile', verbose_name='Profile'),
        ),
        migrations.CreateModel(
            name='TradingOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('state', models.CharField(choices=[('DRAFT', 'draft'), ('TEST', 'test'), ('PUBLISH', 'publish'), ('START', 'start'), ('CLOSE', 'close'), ('DELETED', 'deleted')], default='PUBLISH', max_length=8, verbose_name='State')),
                ('type', models.CharField(choices=[('FUTURES', 'futures'), ('SPOT', 'spot')], default='FUTURES', max_length=8, verbose_name='Type')),
                ('position', models.CharField(blank=True, choices=[('LONG', 'long'), ('SHORT', 'short')], max_length=8, verbose_name='Position')),
                ('exchange', models.CharField(max_length=32, verbose_name='Exchange')),
                ('coin_pair', models.CharField(max_length=32, verbose_name='Coin pair')),
                ('leverage', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Leverage')),
                ('order_type', models.CharField(choices=[('MARKET', 'Market'), ('LIMIT', 'Limit')], default='LIMIT', max_length=32, verbose_name='Order type')),
                ('side', models.CharField(choices=[('BUY', 'Buy'), ('SELL', 'Sell')], default='BUY', max_length=4, verbose_name='Side')),
                ('amount', models.FloatField(blank=True, null=True, verbose_name='Amount')),
                ('price', models.BigIntegerField(blank=True, null=True, verbose_name='Price')),
                ('entry_point', models.BigIntegerField(blank=True, null=True, verbose_name='Price')),
                ('stop_los', models.BigIntegerField(blank=True, null=True, verbose_name='Stop los')),
                ('take_profit', models.BigIntegerField(blank=True, null=True, verbose_name='Take profit')),
                ('service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', related_query_name='order', to='services.service', verbose_name='Service')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CopySetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('margin', models.FloatField(verbose_name='Margin')),
                ('take_profit', models.FloatField(blank=True, null=True, verbose_name='Take profit')),
                ('stop_los', models.FloatField(blank=True, null=True, verbose_name='Stop los')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='copy_settings', related_query_name='copy_setting', to='user.profile', verbose_name='Profile')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='copy_settings', related_query_name='copy_setting', to='services.service', verbose_name='Service')),
            ],
        ),
        migrations.AddField(
            model_name='copytradingorder',
            name='trading_order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='copy_trading_orders', related_query_name='copy_trading_order', to='copytrading.tradingorder', verbose_name='Trading order'),
        ),
    ]