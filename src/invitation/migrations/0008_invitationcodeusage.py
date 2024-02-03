# Generated by Django 3.2 on 2023-10-04 14:36

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0012_profile_quick_signal'),
        ('services', '0045_auto_20230930_1620'),
        ('invitation', '0007_invitationcode_used_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvitationCodeUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('invitation_code', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invitation_code_usages', to='invitation.invitationcode', verbose_name='Invitation code')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='service_invitation_code_usages', to='services.service', verbose_name='Service')),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscription_invitation_code_usages', to='services.subscription', verbose_name='Subscription')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_invitation_code_usages', to='user.profile', verbose_name='User')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]