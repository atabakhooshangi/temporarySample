# Generated by Django 4.2 on 2023-11-05 11:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0031_alter_tradingsignal_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tradingsignal',
            name='pnl_percentage',
            field=models.FloatField(blank=True, db_index=True, null=True, verbose_name='Pnl percentage'),
        ),
    ]