from core.base_model import BaseModelAdmin


class InviteAdmin(BaseModelAdmin):
    list_display = (
        'id',
        "subscriber_iam_id",
        "inviter_id",
        "amount",
        "inviter_referral_code"
    )
    list_editable = ["inviter_id","amount", "inviter_referral_code"]
