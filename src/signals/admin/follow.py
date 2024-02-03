from django.contrib import admin


class UserFollowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'user__username', 'following_id', 'following__username')
    list_filter = ('id', 'user_id', 'user__username', 'following_id', 'following__username')

    def user__username(self, obj):
        return obj.user.username

    def following__username(self, obj):
        return obj.following.username


class VendorFollowerAdmin(admin.ModelAdmin):
    list_display = ('id', 'vendor_id', 'vendor__username', 'follower_id', 'follower__username',)
    list_filter = ['vendor__username', 'follower__username', 'vendor_id', 'follower_id']

    def vendor__username(self, obj):
        return obj.vendor.username

    def follower__username(self, obj):
        return obj.follower.username
