
from django.contrib import admin
from media.models import Media
from .media import MediaAdmin

admin.site.register(Media, MediaAdmin)
