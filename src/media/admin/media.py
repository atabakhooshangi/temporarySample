from django.contrib import admin


class MediaAdmin(admin.ModelAdmin):
    list_display = ("key", "bucket", "external_media_url")
    search_fields = ("key", "bucket")
