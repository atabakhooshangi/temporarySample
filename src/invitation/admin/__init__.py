from django.contrib import admin
from .invite_bonus import InviteAdmin
from .invitation_code import InvitationCodeAdmin, AssigneeEntitiesAdmin, InvitationReferralAdmin
from invitation.models import InviteBonus, InvitationCode, AssigneeEntities, InvitationReferral

admin.site.register(InviteBonus, InviteAdmin)
admin.site.register(InvitationCode, InvitationCodeAdmin)
admin.site.register(AssigneeEntities, AssigneeEntitiesAdmin)
admin.site.register(InvitationReferral, InvitationReferralAdmin)
