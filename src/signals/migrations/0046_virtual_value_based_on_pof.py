from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0044_alter_signalvirtualbalance_balance'),
    ]

    def fill_virtual_values(apps, schema_editor):
        signal_model = apps.get_model('signals', 'TradingSignal')

        for signal in signal_model.objects.all():
            signal.virtual_value = signal.percentage_of_fund * 10 # because the default value is 1000 in pof and the formula is pof /100 * 1000 . just made it short
            signal.save()



    operations = [
        migrations.RunPython(code=fill_virtual_values, reverse_code=migrations.RunPython.noop)
    ]
