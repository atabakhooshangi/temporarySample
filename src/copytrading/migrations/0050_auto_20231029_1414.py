# Generated by Django 3.2 on 2023-10-29 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0049_merge_20231020_1247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='position',
            name='avg_entry_price',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True, verbose_name='Avg Entry Price'),
        ),
        migrations.AlterField(
            model_name='position',
            name='avg_exit_price',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True, verbose_name='Avg Exit point'),
        ),
        migrations.AlterField(
            model_name='position',
            name='closed_pnl_percentage',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=5, verbose_name='Closed pnl percentage'),
        ),
        migrations.AlterField(
            model_name='position',
            name='status',
            field=models.CharField(blank=True, choices=[('OPEN', 'Open'), ('CLOSED', 'Closed'), ('CANCELED', 'Canceled'), ('X_CLOSED', 'X Closed')], default='OPEN', max_length=20, verbose_name='Status'),
        ),
    ]