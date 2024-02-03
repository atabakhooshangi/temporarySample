# Generated by Django 3.2 on 2023-09-17 13:06

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('invitation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InviteBonus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('subscriber_iam_id', models.PositiveIntegerField(unique=True)),
                ('inviter_id', models.IntegerField(blank=True, null=True)),
                ('additional_data', models.JSONField(blank=True, default=dict, null=True)),
            ],
            options={
                'verbose_name': 'Invite Bonus',
                'verbose_name_plural': 'Invite Bonuses',
                'ordering': ['-created_at'],
            },
        ),
    ]