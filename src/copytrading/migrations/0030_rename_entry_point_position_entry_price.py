# Generated by Django 3.2 on 2023-05-23 13:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0029_auto_20230523_1347'),
    ]

    operations = [
        migrations.RenameField(
            model_name='position',
            old_name='entry_point',
            new_name='entry_price',
        ),
    ]
