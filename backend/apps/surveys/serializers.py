"""
Serializers for surveys domain.
"""
from rest_framework import serializers

from apps.surveys.models import (
    SurveyInstance,
    SurveyInvitation,
    SurveyQuestion,
    SurveyResponse,
    SurveyTemplate,
)


class SurveyTemplateSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(source="questions.count", read_only=True)

    class Meta:
        model = SurveyTemplate
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "survey_type",
            "is_active",
            "thank_you_message",
            "question_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "question_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class SurveyQuestionSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = SurveyQuestion
        fields = [
            "id",
            "organization",
            "template",
            "template_name",
            "question_text",
            "question_type",
            "options",
            "is_required",
            "order",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "template_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class SurveyInstanceSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True, default=None
    )
    job_title = serializers.CharField(source="job.title", read_only=True, default=None)
    response_count = serializers.IntegerField(source="responses.count", read_only=True)
    invitation_count = serializers.IntegerField(source="invitations.count", read_only=True)

    class Meta:
        model = SurveyInstance
        fields = [
            "id",
            "organization",
            "template",
            "template_name",
            "candidate",
            "candidate_name",
            "job",
            "job_title",
            "status",
            "token",
            "sent_at",
            "completed_at",
            "anonymous",
            "response_count",
            "invitation_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "template_name",
            "candidate_name",
            "job_title",
            "token",
            "sent_at",
            "completed_at",
            "response_count",
            "invitation_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class SurveyResponseSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.question_text", read_only=True)
    question_type = serializers.CharField(source="question.question_type", read_only=True)

    class Meta:
        model = SurveyResponse
        fields = [
            "id",
            "organization",
            "instance",
            "question",
            "question_text",
            "question_type",
            "answer",
            "answered_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SurveyInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyInvitation
        fields = [
            "id",
            "organization",
            "instance",
            "email",
            "status",
            "sent_at",
            "completed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "status",
            "sent_at",
            "completed_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class PublicSurveySubmitSerializer(serializers.Serializer):
    instance_id = serializers.UUIDField(required=False)
    question_id = serializers.UUIDField()
    answer = serializers.JSONField()


class SurveyAnalyticsSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()
