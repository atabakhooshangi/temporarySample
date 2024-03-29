# Generated by Django 4.2 on 2023-12-10 01:02

from django.db import migrations, models


class Migration(migrations.Migration):

    def forwards_func(apps, schema_editor):
        service_model = apps.get_model('services', 'Service')
        for service in service_model.objects.all():
            if not hasattr(service, 'virtual_value'):
                signal_virtual_model = apps.get_model('signals', 'SignalVirtualBalance')
                signal_virtual_model.objects.create(
                    service=service,
                    balance=10_000,
                )

    dependencies = [
        ('signals', '0041_alter_tradingsignal_virtual_value'),
    ]

    operations = [
        migrations.RunPython(code=forwards_func, reverse_code=migrations.RunPython.noop)
    ]
