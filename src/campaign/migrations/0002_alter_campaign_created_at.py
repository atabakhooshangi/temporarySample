# Generated by Django 4.2 on 2023-11-05 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaign", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
