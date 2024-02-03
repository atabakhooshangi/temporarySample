from django.db import migrations, models


class Migration(migrations.Migration):

    def forwards_func(apps, schema_editor):
        service_model = apps.get_model('services', 'Service')
        for service in service_model.objects.all():
            if not hasattr(service, 'virtual_value'):
                signal_virtual_model = apps.get_model('signals', 'SignalVirtualBalance')
                signal_virtual_model.objects.create(
                    service=service,
                    balance=1_000,
                )
            else:
                service.virtual_value.balance = 1_000
                service.virtual_value.save()

    dependencies = [
        ('signals', '0044_alter_signalvirtualbalance_balance'),
    ]

    operations = [
        migrations.RunPython(code=forwards_func, reverse_code=migrations.RunPython.noop)
    ]