from django.contrib import admin
from django.db import models
from django.utils import timezone
from adminsortable2.admin import SortableAdminMixin


class BaseModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(is_deleted=True)


class BaseModelClass(models.Model):
    objects = BaseModelManager()
    created_at = models.DateTimeField(auto_now_add=True,
                                      # default=timezone.now,
                                      null=False,
                                      blank=False,
                                      db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True


class BaseModelAdmin(SortableAdminMixin, admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")

    ordering = ('-created_at',)

    def has_delete_permission(self, request, obj=None):
        # Disable delete
        return False

    class Meta:
        abstract = True
