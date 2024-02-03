
from django.contrib import admin
from django.contrib.auth import get_user_model

from user.models import Profile, VendorProfileAnalytic
from .user import UserAdmin
from .profile import ProfileAdmin, VendorProfileAnalyticAdmin


User = get_user_model()


admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(VendorProfileAnalytic, VendorProfileAnalyticAdmin)