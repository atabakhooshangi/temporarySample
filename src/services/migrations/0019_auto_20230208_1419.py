# Generated by Django 3.2 on 2023-02-08 14:19

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    db_alias = schema_editor.connection.alias
    Service.objects.using(db_alias).filter(exchanges__isnull=False).update(exchanges=[])
    Service.objects.using(db_alias).filter(watch_list__isnull=False).update(watch_list=[])


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0018_alter_service_watch_list'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='service',
            name='exchange',
        ),
        migrations.AddField(
            model_name='service',
            name='exchanges',
            field=models.JSONField(default=dict, verbose_name='Exchange'),
        ),
        migrations.AlterField(
            model_name='service',
            name='watch_list',
            field=models.JSONField(default=dict, verbose_name='watch_list'),
        ),
        migrations.RunPython(forwards_func, reverse_func)
    ]
