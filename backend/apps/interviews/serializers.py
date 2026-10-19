"""
Serializers for interviews domain.
"""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.interviews.models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    InterviewKit,
    InterviewPanel,
    Scorecard,
)

User = get_user_model()


class InterviewKitSerializer(serializers.ModelSerializer)
    class Meta:
        model = InterviewKit
        fields = [
            "id",
            "name",
            "description",
            "questions",
            "score_dimensions",
            "duration_minutes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewPanelSerializer(serializers.ModelSerializer):
    member_ids = serializers.PrimaryKeyRelatedField(
        source="members",
        many=True,
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = InterviewPanel
        fields = [
            "id",
            "name",
            "description",
            "member_ids",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterviewerAssignmentSerializer(serializers.ModelSerializer):
    interviewer_email = serializers.EmailField(source="interviewer.email", read_only=True)
    interviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = InterviewerAssignment
        fields = [
            "id",
            "interview",
            "interviewer",
            "interviewer_email",
            "interviewer_name",
            "role",
            "response_status",
            "is_required",
            "created_at",
        ]
        read_only_fields = ["id", "interview", "created_at"]

    def get_interviewer_name(self, obj):
        return obj.interviewer.get_full_name() or obj.interviewer.email


class InterviewerAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewerAvailability
        fields = [
            "id",
            "interviewer",
            "start",
            "end",
            "timezone",
            "is_recurring",
            "recurrence_rule",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start", getattr(self.instance, "start", None))
        end = attrs.get("end", getattr(self.instance, "end", None))
        if start and end and end >= start:
            raise serializers.ValidationError({"end": "End must be after start."})
        return attrs


class ScorecardSerializer(serializers.ModelSerializer):
    interviewer_email = serializers.EmailField(source="interviewer.email", read_only=True)

    class Meta:
        model = Scorecard
        fields = [
            "id",
            "interview",
            "interviewer",
            "interviewer_email",
            "assignment",
            "scores",
            "overall_score",
            "recommendation",
            "strengths",
            "concerns",
            "private_notes",
            "submitted_at",
            "is_submitted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "overall_score",
            "submitted_at",
            "is_submitted",
            "created_at",
            "updated_at",
        ]


class InterviewDecisionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewDecisionSummary
        fields = [
            "id",
            "interview",
            "application",
            "decision",
            "average_score",
            "recommendation_tally",
            "scorecard_count",
            "summary",
            "decided_by",
            "decided_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class InterviewListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id",
            "application",
            "job",
            "candidate",
            "candidate_name",
            "interview_type",
            "status",
            "title",
            "scheduled_start",
            "scheduled_end",
            "timezone",
            "meeting_url",
            "created_at",
        ]


class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    assignments = InterviewerAssignmentSerializer(many=True, read_only=True)
    scorecards = ScorecardSerializer(many=True, read_only=True)
    decision_summary = InterviewDecisionSummarySerializer(read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id",
            "application",
            "job",
            "job_title",
            "candidate",
            "candidate_name",
            "kit",
            "panel",
            "interview_type",
            "status",
            "title",
            "location",
            "meeting_url",
            "scheduled_start",
            "scheduled_end",
            "timezone",
            "notes",
            "cancellation_reason",
            "cancelled_at",
            "reminder_sent_at",
            "metadata",
            "assignments",
            "scorecards",
            "decision_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "job",
            "status",
            "cancelled_at",
            "reminder_sent_at",
            "assignments",
            "scorecards",
            "decision_summary",
            "created_at",
            "updated_at",
        ]


class ScheduleInterviewSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    interviewer_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    kit_id = serializers.UUIDField(required=False, allow_null=True)
    panel_id = serializers.UUIDField(required=False, allow_null=True)
    interview_type = serializers.ChoiceField(
        choices=Interview.InterviewType.choices, default=Interview.InterviewType.VIDEO
    )
    title = serializers.CharField(required=False, allow_blank=True, default="")
    location = serializers.CharField(required=False, allow_blank=True, default="")
    meeting_url = serializers.URLField(required=False, allow_blank=True, default="")
    timezone = serializers.CharField(required=False, default="UTC")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CancelInterviewSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SubmitScorecardSerializer(serializers.Serializer):
    scores = serializers.DictField(required=False, default=dict)
    recommendation = serializers.ChoiceField(
        choices=Scorecard.Recommendation.choices, default=Scorecard.Recommendation.STRONG_YES
    )
    strengths = serializers.CharField(required=False, allow_blank=True, default="")
    concerns = serializers.CharField(required=False, allow_blank=True, default="")
    private_notes = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=InterviewDecisionSummary.Decision.choices)


class AvailabilitySlotsSerializer(serializers.Serializer):
    interviewer_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    duration_minutes = serializers.IntegerField(default=60, min_value=15)
    window_start = serializers.DateTimeField(required=False)
    window_end = serializers.DateTimeField(required=False)
    slot_step_minutes = serializers.IntegerField(default=30, min_value=5)
