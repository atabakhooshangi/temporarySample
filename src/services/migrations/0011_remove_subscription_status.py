# Generated by Django 3.2 on 2023-01-16 21:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0010_auto_20230116_2137'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='status',
        ),
    ]
