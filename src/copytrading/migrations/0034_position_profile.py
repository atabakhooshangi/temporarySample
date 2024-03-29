# Generated by Django 3.2 on 2023-05-27 15:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_iamadmin'),
        ('copytrading', '0033_alter_position_closed_pnl_percentage'),
    ]

    operations = [
        migrations.AddField(
            model_name='position',
            name='profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='positions', related_query_name='position', to='user.profile', verbose_name='Profile'),
        ),
    ]
