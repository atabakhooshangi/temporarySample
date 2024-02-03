# Generated by Django 3.2 on 2023-07-22 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0038_auto_20230712_1127'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='service',
            name='draw_down',
        ),
        migrations.AddField(
            model_name='service',
            name='draw_down',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Draw Down'),
        ),

        migrations.RemoveField(
            model_name='service',
            name='initial_draw_down',
        ),
        migrations.AddField(
            model_name='service',
            name='initial_draw_down',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Initial Draw Down'),
        ),
    ]
