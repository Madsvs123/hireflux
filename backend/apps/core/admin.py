from django.contrib import admin

from apps.core.models import AuditLog, Notification


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "resource_type",
        "resource_id",
        "actor",
        "organization",
    )
    list_filter = ("action", "resource_type", "organization")
    search_fields = ("message", "resource_id", "actor__email", "request_id")
    readonly_fields = (
        "id",
        "organization",
        "actor",
        "action",
        "resource_type",
        "resource_id",
        "message",
        "metadata",
        "ip_address",
        "user_agent",
        "request_id",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "level", "is_read", "organization", "created_at")
    list_filter = ("level", "is_read", "category")
    search_fields = ("title", "body", "recipient__username")
    raw_id_fields = ("recipient", "organization")
