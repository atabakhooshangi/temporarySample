from django.contrib.auth.models import Group
from django.db import migrations, models


class Migration(migrations.Migration):
    def forwards_func(apps, schema_editor):
        Group.objects.get_or_create(name='support')

    dependencies = [
        ('services', '0042_alter_roihistory_history_type'),
    ]

    operations = [
        migrations.RunPython(code=forwards_func, reverse_code=migrations.RunPython.noop)
    ]
