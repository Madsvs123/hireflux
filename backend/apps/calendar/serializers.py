"""
Serializers for calendar (interview scheduling) domain.
"""
from rest_framework import serializers

from apps.calendar.models import (
    AvailabilityRule,
    BookingRequest,
    CalendarAccount,
    InterviewSlot,
    SchedulingLink,
)


class CalendarAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarAccount
        fields = [
            "id",
            "user",
            "provider",
            "email",
            "calendar_id",
            "is_primary",
            "sync_enabled",
            "last_synced_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_synced_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class AvailabilityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilityRule
        fields = [
            "id",
            "user",
            "title",
            "days_of_week",
            "start_time",
            "end_time",
            "timezone",
            "buffer_minutes",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def validate(self, attrs):
        days = attrs.get("days_of_week", getattr(self.instance, "days_of_week", []))
        for day in days:
            if not isinstance(day, int) or day < 0 or day >= 6:
                raise serializers.ValidationError(
                    {"days_of_week": "Each day must be an integer 0 (Monday) through 6 (Sunday)."}
                )
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class InterviewSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSlot
        fields = [
            "id",
            "availability_rule",
            "user",
            "start_at",
            "end_at",
            "status",
            "held_until",
            "booking_request",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SchedulingLinkSerializer(serializers.ModelSerializer):
    booking_count = serializers.IntegerField(source="booking_requests.count", read_only=True)

    class Meta:
        model = SchedulingLink
        fields = [
            "id",
            "name",
            "slug",
            "owner",
            "job",
            "duration_minutes",
            "start_date",
            "end_date",
            "availability_rules",
            "timezone",
            "is_active",
            "booking_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "booking_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        owner = attrs.get("owner", getattr(self.instance, "owner", None))
        if owner is not None and request is not None:
            org = getattr(request, "organization", None)
            if org is not None and not owner.memberships.filter(organization=org, is_active=True).exists():
                raise serializers.ValidationError(
                    {"owner": "Owner must be an active member of this organization."}
                )
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be after start date."})
        return attrs


class BookingRequestSerializer(serializers.ModelSerializer):
    link_name = serializers.CharField(source="scheduling_link.name", read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)

    class Meta:
        model = BookingRequest
        fields = [
            "id",
            "scheduling_link",
            "link_name",
            "candidate",
            "candidate_name",
            "name",
            "email",
            "requested_slot_start",
            "status",
            "confirmation_token",
            "confirmed_at",
            "meeting_url",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "confirmation_token",
            "confirmed_at",
            "meeting_url",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        link = attrs.get("scheduling_link", getattr(self.instance, "scheduling_link", None))
        if link is not None and request is not None:
            org = getattr(request, "organization", None)
            if org is not None and link.organization_id != org.pk:
                raise serializers.ValidationError(
                    {"scheduling_link": "Scheduling link does not belong to this organization."}
                )
        return attrs


class BulkGenerateSlotsSerializer(serializers.Serializer):
    user = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_minutes = serializers.IntegerField(min_value=15, max_value=480, default=60)
    rule_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class HoldSlotSerializer(serializers.Serializer):
    hold_minutes = serializers.IntegerField(min_value=5, max_value=1440, default=30)


class PublicBookingSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    requested_slot_start = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
