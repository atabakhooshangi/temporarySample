# Generated by Django 3.2 on 2023-08-27 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0041_auto_20230729_0928'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roihistory',
            name='history_type',
            field=models.CharField(choices=[('WEEKLY', 'weekly'), ('TWO_WEEKLY', 'two_weekly'), ('MONTHLY', 'monthly'), ('TWO_MONTHLY', 'two_monthly'), ('THREE_MONTHLY', 'three_monthly'), ('OVERALLY', 'overally')], max_length=16, verbose_name='History type'),
        ),
    ]
