# Generated by Django 3.2 on 2023-06-25 08:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0021_auto_20230625_0747'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tradingsignal',
            old_name='child_id',
            new_name='child',
        ),
        migrations.RenameField(
            model_name='tradingsignal',
            old_name='parent_id',
            new_name='parent',
        ),
    ]
