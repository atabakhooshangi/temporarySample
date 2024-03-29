# Generated by Django 3.2 on 2023-05-14 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('copytrading', '0017_auto_20230510_0928'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='position',
            name='exit_point',
        ),
        migrations.RemoveField(
            model_name='position',
            name='position',
        ),
        migrations.RemoveField(
            model_name='position',
            name='realised_pnl',
        ),
        migrations.AddField(
            model_name='position',
            name='avg_entry_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True, verbose_name='Avg Entry Price'),
        ),
        migrations.AddField(
            model_name='position',
            name='avg_exit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Avg Exit point'),
        ),
        migrations.AddField(
            model_name='position',
            name='closed_pnl',
            field=models.DecimalField(decimal_places=4, default=0.0, max_digits=7, verbose_name='Closed Pnl'),
        ),
        migrations.AddField(
            model_name='position',
            name='side',
            field=models.CharField(blank=True, choices=[('LONG', 'long'), ('SHORT', 'short')], max_length=10, verbose_name='Side'),
        ),
        migrations.AlterField(
            model_name='position',
            name='status',
            field=models.CharField(blank=True, choices=[('OPEN', 'Open'), ('CLOSED', 'Closed')], default='OPEN', max_length=20, verbose_name='Status'),
        ),
        migrations.AlterField(
            model_name='position',
            name='unrealised_pnl',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=7, null=True, verbose_name='Unrealised Pnl'),
        ),
    ]
