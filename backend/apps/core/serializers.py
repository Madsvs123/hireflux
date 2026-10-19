"""
Serializers for core resources.
"""
from rest_framework import serializers

from apps.core.models import AuditLog, Notification


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "organization",
            "actor",
            "actor_email",
            "actor_name",
            "action",
            "resource_type",
            "resource_id",
            "message",
            "metadata",
            "ip_address",
            "user_agent",
            "request_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj)
        if not obj.actor:
            return None
        return obj.actor.get_full_name()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "organization",
            "recipient",
            "title",
            "body",
            "level",
            "category",
            "link",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "title",
            "body",
            "level",
            "category",
            "link",
            "data",
            "read_at",
            "created_at",
            "updated_at",
        ]
