# Generated by Django 3.2 on 2023-01-25 13:05

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    db_alias = schema_editor.connection.alias
    Service.objects.using(db_alias).filter(subscription_fee__isnull=True).update(subscription_fee=0)


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('services', '0013_service_platform_fee'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='subscription_fee',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Subscription fee'),
        ),
        migrations.RunPython(forwards_func,reverse_func)
    ]
