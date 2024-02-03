# Generated by Django 3.2 on 2023-01-08 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_alter_service_profile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='coin',
            field=models.CharField(choices=[('USDT', 'usdt'), ('IRR', 'irr')], max_length=16, verbose_name='Coin'),
        ),
        migrations.AlterField(
            model_name='service',
            name='subscription_coin',
            field=models.CharField(choices=[('USDT', 'usdt'), ('IRR', 'irr')], max_length=16, verbose_name='Subscription coin'),
        ),
    ]