# Generated by Django 4.2 on 2023-11-16 21:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0053_service_history_used'),
        ('signals', '0034_alter_comment_created_at_alter_comment_is_deleted_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tradingsignal',
            name='virtual_value',
            field=models.FloatField(blank=True, null=True, verbose_name='Virtual Value'),
        ),
        migrations.CreateModel(
            name='SignalVirtualBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('balance', models.FloatField(default=1000, verbose_name='Balance')),
                ('frozen', models.FloatField(default=0, verbose_name='Frozen Balance')),
                ('service', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='services.service', verbose_name='Service id')),
            ],
            options={
                'verbose_name': 'Signal Virtual Balance',
                'verbose_name_plural': 'Signal Virtual Balances',
                'ordering': ('-created_at',),
            },
        ),
    ]
