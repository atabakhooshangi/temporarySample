# Generated by Django 4.2 on 2023-11-05 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0012_profile_quick_signal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
