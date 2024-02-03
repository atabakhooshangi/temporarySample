from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0054_dailyaggregatedpnl_v_balance_and_more')
    ]

    def fill_pnls(apps, schema_editor):
        service_model = apps.get_model('services', 'Service')
        for service in service_model.objects.all():
            if not hasattr(service, 'virtual_value'):
                signal_virtual_model = apps.get_model('signals', 'SignalVirtualBalance')
                signal_virtual_model.objects.create(
                    service=service,
                    balance=10_000,
                )

        dailAggregateModel = apps.get_model('services', 'DailyAggregatedPnl')
        latest_pnls_subquery = dailAggregateModel.objects \
                                   .filter(service=models.OuterRef('service')) \
                                   .order_by('-date') \
                                   .values('id')[:1]

        latest_pnls = dailAggregateModel.objects.filter(
            id=models.Subquery(latest_pnls_subquery)
        )
        for pnl in latest_pnls:
            if pnl.service.service_type == 'SIGNAL':
                pnl.v_balance = pnl.service.virtual_value.balance
                pnl.v_balance_change = 0
                pnl.save()



    operations = [
        migrations.RunPython(code=fill_pnls, reverse_code=migrations.RunPython.noop)
    ]
