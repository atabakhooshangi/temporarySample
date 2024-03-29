# Generated by Django 4.2 on 2023-12-05 11:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0053_service_history_used'),
        ('signals', '0038_alter_tradingsignal_virtual_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='signalvirtualbalance',
            name='service',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='virtual_value', to='services.service', verbose_name='Service id'),
        ),
    ]
