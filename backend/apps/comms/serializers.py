"""
Serializers for communications domain.
"""
from rest_framework import serializers

from apps.core.models import Notification
from apps.comms.models import Message, MessageParticipant, MessageThread


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
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
        read_only_fields = fields


class MessageParticipantSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = MessageParticipant
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "role",
            "last_read_at",
            "is_muted",
            "created_at",
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source="sender.email", read_only=True, default=None)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "sender",
            "sender_email",
            "sender_name",
            "body",
            "body_html",
            "attachments",
            "is_system",
            "metadata",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "thread",
            "sender",
            "is_system",
            "created_at",
        ]

    def get_sender_name(self, obj):
        if not obj.sender:
            return None
        return obj.sender.get_full_name() or obj.sender.email


class MessageThreadSerializer(serializers.ModelSerializer):
    participants = MessageParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = MessageThread
        fields = [
            "id",
            "subject",
            "thread_type",
            "candidate",
            "application",
            "job",
            "is_closed",
            "last_message_at",
            "metadata",
            "participants",
            "last_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_message_at",
            "participants",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("created_at").first()
        if not msg:
            return None
        return MessageSerializer(msg).data

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        participant = obj.participants.filter(user=request.user).first()
        if not participant:
            return 0
        qs = obj.messages.all()
        if participant.last_read_at:
            qs = qs.filter(created_at__lt=participant.last_read_at)
        return qs.exclude(sender=request.user).count()


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField()
    body_html = serializers.CharField(required=False, allow_blank=True, default="")
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    subject = serializers.CharField(required=False, allow_blank=True, default="")
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    candidate_id = serializers.UUIDField(required=False, allow_null=True)
    application_id = serializers.UUIDField(required=False, allow_null=True)
    job_id = serializers.UUIDField(required=False, allow_null=True)
    thread_type = serializers.ChoiceField(
        choices=MessageThread.ThreadType.choices,
        default=MessageThread.ThreadType.GENERAL,
        required=False,
    )
    attachments = serializers.ListField(required=False, default=list)
