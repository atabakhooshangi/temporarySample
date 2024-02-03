# Generated by Django 3.2 on 2023-01-01 15:33

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_alter_profile_state'),
        ('signals', '0003_auto_20221221_0731'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tradingsignal',
            name='percentage_of_found',
        ),
        migrations.AddField(
            model_name='tradingsignal',
            name='closed_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Closed datetime'),
        ),
        migrations.AddField(
            model_name='tradingsignal',
            name='percentage_of_fund',
            field=models.IntegerField(default=100, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Percentage of fund'),
        ),
        migrations.AddField(
            model_name='tradingsignal',
            name='pnl_amount',
            field=models.FloatField(blank=True, null=True, verbose_name='Pnl amount'),
        ),
        migrations.AddField(
            model_name='tradingsignal',
            name='pnl_percentage',
            field=models.FloatField(blank=True, null=True, verbose_name='Pnl percentage'),
        ),
        migrations.AddField(
            model_name='tradingsignal',
            name='start_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Start datetime'),
        ),
        migrations.CreateModel(
            name='ROIHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('history_type', models.CharField(choices=[('WEEKLY', 'weekly'), ('MONTHLY', 'monthly')], max_length=16, verbose_name='History type')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_ready', models.BooleanField(default=False)),
                ('vendor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roi_history_vendors', related_query_name='roi_history_vendor', to='user.profile', verbose_name='Vendor')),
            ],
        ),
        migrations.CreateModel(
            name='DailyROI',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percentage', models.FloatField(verbose_name='Percentage')),
                ('date', models.DateField(unique=True, verbose_name='Date')),
                ('roi_history', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rois', related_query_name='roi', to='signals.roihistory')),
            ],
        ),
        migrations.AddConstraint(
            model_name='roihistory',
            constraint=models.UniqueConstraint(fields=('vendor', 'history_type'), name='unique_history_type_per_vendor'),
        ),
    ]
