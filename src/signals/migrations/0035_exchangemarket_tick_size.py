# Generated by Django 4.2 on 2023-11-20 08:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0034_alter_comment_created_at_alter_comment_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="exchangemarket",
            name="tick_size",
            field=models.FloatField(default=1.0, verbose_name="Tick Size"),
        ),
    ]
