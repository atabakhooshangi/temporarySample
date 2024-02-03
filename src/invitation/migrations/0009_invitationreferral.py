# Generated by Django 3.2 on 2023-10-21 08:40

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('invitation', '0008_invitationcodeusage'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvitationReferral',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('owner_id', models.PositiveBigIntegerField(verbose_name='owner id')),
                ('referral_code', models.TextField(verbose_name='Referral code')),
                ('seen', models.BooleanField(default=False, verbose_name='Seen')),
                ('invitation_code', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invitation_code_invitation_referrals', to='invitation.invitationcode', verbose_name='Invitation code')),
            ],
            options={
                'unique_together': {('owner_id', 'referral_code')},
            },
        ),
    ]