"""
Candidate portal serializers.
"""
from rest_framework import serializers

from apps.assessments.models import AssessmentAssignment
from apps.candidates.models import CandidateDocument
from apps.comms.models import Message, MessageThread
from apps.interviews.models import Interview
from apps.offers.models import Offer
from apps.pipelines.models import Application


class PortalApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    job_slug = serializers.CharField(source="job.slug", read_only=True)
    stage_name = serializers.CharField(source="stage.stage_type", read_only=True, default=None)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "job_title",
            "job_slug",
            "organization",
            "organization_name",
            "stage",
            "stage_name",
            "status",
            "applied_at",
            "stage_entered_at",
            "hired_at",
            "rejected_at",
            "cover_letter",
        ]


class PortalApplicationStatusSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    status = serializers.CharField()
    stage_name = serializers.CharField(allow_null=True)
    stage_type = serializers.CharField(allow_null=True)
    applied_at = serializers.DateTimeField()
    stage_entered_at = serializers.DateTimeField(allow_null=True)
    message = serializers.CharField()


class PortalInterviewSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Interview
        fields = [
            "id",
            "application",
            "job",
            "job_title",
            "interview_type",
            "status",
            "title",
            "location",
            "meeting_url",
            "scheduled_start",
            "scheduled_end",
            "timezone",
        ]


class PortalAssessmentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    instructions = serializers.CharField(source="template.instructions", read_only=True)
    time_limit_minutes = serializers.IntegerField(
        source="template.time_limit_minutes", read_only=True, allow_null=True
    )

    class Meta:
        model = AssessmentAssignment
        fields = [
            "id",
            "template",
            "template_name",
            "application",
            "job",
            "status",
            "due_at",
            "started_at",
            "submitted_at",
            "score_percent",
            "passed",
            "instructions",
            "time_limit_minutes",
        ]


class PortalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateDocument
        fields = [
            "id",
            "doc_type",
            "title",
            "file",
            "file_name",
            "content_type",
            "file_size",
            "is_primary",
            "created_at",
        ]
        read_only_fields = ["id", "file_name", "content_type", "file_size", "created_at"]


class PortalDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    doc_type = serializers.ChoiceField(
        choices=CandidateDocument.DocType.choices, default=CandidateDocument.DocType.RESUME
    )
    title = serializers.CharField(required=False, allow_blank=True, default="")
    is_primary = serializers.BooleanField(default=False)
    candidate_id = serializers.UUIDField(required=False, allow_null=True)


class PortalOfferSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="job.title", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "application",
            "job",
            "job_title",
            "organization_name",
            "status",
            "title",
            "salary",
            "salary_max",
            "currency",
            "equity",
            "bonus",
            "benefits",
            "start_date",
            "expires_at",
            "employment_type",
            "work_location",
            "body_html",
            "body_text",
            "sent_at",
            "responded_at",
        ]


class PortalOfferRespondSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class PortalMessageThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageThread
        fields = [
            "id",
            "subject",
            "thread_type",
            "application",
            "job",
            "is_closed",
            "last_message_at",
            "created_at",
        ]


class PortalMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "body", "body_html", "created_at", "is_system"]


class PortalSendMessageSerializer(serializers.Serializer):
    body = serializers.CharField()
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    application_id = serializers.UUIDField(required=False, allow_null=True)
    subject = serializers.CharField(required=False, allow_blank=True, default="")


class PortalAssessmentSubmitSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.DictField(), min_length=1)
