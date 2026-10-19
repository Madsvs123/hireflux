"""
Serializers for events domain.
"""
from rest_framework import serializers

from apps.events.models import EventRegistration, EventSession, EventTask, RecruitingEvent


class RecruitingEventSerializer(serializers.ModelSerializer):
    session_count = serializers.IntegerField(source="sessions.count", read_only=True)
    registration_count = serializers.IntegerField(source="registrations.count", read_only=True)

    class Meta:
        model = RecruitingEvent
        fields = [
            "id",
            "name",
            "event_type",
            "description",
            "location",
            "is_virtual",
            "start_at",
            "end_at",
            "capacity",
            "status",
            "cover_image",
            "session_count",
            "registration_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "session_count",
            "registration_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        if start_at and end_at and end_at < start_at:
            raise serializers.ValidationError({"end_at": "End time must be after start time."})
        return attrs


class EventSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSession
        fields = [
            "id",
            "event",
            "title",
            "speaker",
            "start_at",
            "end_at",
            "description",
            "room",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        event = attrs.get("event", getattr(self.instance, "event", None))
        if event is not None and request is not None:
            org = getattr(request, "organization", None)
            if org is not None and event.organization_id != org.pk:
                raise serializers.ValidationError({"event": "Event does not belong to this organization."})
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError({"end_at": "End time must be after start time."})
        return attrs


class EventRegistrationSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)

    class Meta:
        model = EventRegistration
        fields = [
            "id",
            "event",
            "event_name",
            "candidate",
            "candidate_name",
            "email",
            "first_name",
            "last_name",
            "status",
            "registered_at",
            "checked_in_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "registered_at",
            "checked_in_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        event = attrs.get("event", getattr(self.instance, "event", None))
        if event is not None and request is not None:
            org = getattr(request, "organization", None)
            if org is not None and event.organization_id != org.pk:
                raise serializers.ValidationError({"event": "Event does not belong to this organization."})
        return attrs


class EventTaskSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)

    class Meta:
        model = EventTask
        fields = [
            "id",
            "event",
            "event_name",
            "title",
            "assignee",
            "due_at",
            "status",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_by", "updated_by", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        event = attrs.get("event", getattr(self.instance, "event", None))
        if event is not None and request is not None:
            org = getattr(request, "organization", None)
            if org is not None and event.organization_id != org.pk:
                raise serializers.ValidationError({"event": "Event does not belong to this organization."})
        return attrs


class CheckInManySerializer(serializers.Serializer):
    registration_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
