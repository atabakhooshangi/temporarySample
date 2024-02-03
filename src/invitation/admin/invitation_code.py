from core.base_model import BaseModelAdmin


class InvitationCodeAdmin(BaseModelAdmin):
    list_display = (
        'id',
        "code_string",
        "assignor_type",
        "invitation_type",
        "user_limit",
        "used_count",
        "start_date",
        "expire_date",
    )


class AssigneeEntitiesAdmin(BaseModelAdmin):
    list_display = (
        'id',
        "invitation",
    )


class InvitationReferralAdmin(BaseModelAdmin):
    list_display = (
        'id',
        "owner_id",
        "referral_code",
        "invitation_code",
    )
