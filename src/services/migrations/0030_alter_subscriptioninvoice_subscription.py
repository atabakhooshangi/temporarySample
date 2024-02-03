# Generated by Django 3.2 on 2023-04-09 13:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0029_subscription_start_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptioninvoice',
            name='subscription',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='invoices', related_query_name='invoice', to='services.subscription', verbose_name='Subscription'),
        ),
    ]