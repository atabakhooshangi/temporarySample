# Generated by Django 3.2 on 2023-05-17 18:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0022_alter_position_side'),
    ]

    operations = [
        migrations.RenameField(
            model_name='position',
            old_name='closed_datetime',
            new_name='closed_at',
        ),
    ]
