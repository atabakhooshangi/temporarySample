from django.db import migrations
from django.shortcuts import get_object_or_404


def forwards_func(apps, schema_editor):
    Profile = apps.get_model("user", "Profile")
    db_alias = schema_editor.connection.alias
    try:
        user = Profile.objects.using(db_alias).get(id=15)
        user.default_name = False
        user.save()
    except Profile.DoesNotExist:
        pass


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('user', '0004_profile_default_name'),
    ]
    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
