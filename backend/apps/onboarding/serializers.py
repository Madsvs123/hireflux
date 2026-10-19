"""
Serializers for onboarding domain.
"""
from rest_framework import serializers

from apps.onboarding.models import (
    OnboardingDocument,
    OnboardingPlan,
    OnboardingPlanTask,
    OnboardingTaskDefinition,
    OnboardingTemplate,
)


class OnboardingTemplateSerializer(serializers.ModelSerializer):
    task_definitions = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTemplate
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "config",
            "task_definitions",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "task_definitions",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_task_definitions(self, obj):
        return OnboardingTaskDefinitionSerializer(
            obj.task_definitions.all(), many=True
        ).data


class OnboardingTaskDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTaskDefinition
        fields = [
            "id",
            "template",
            "title",
            "description",
            "owner_role",
            "due_offset_days",
            "required",
            "order",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class OnboardingPlanSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.email", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)
    offer_title = serializers.CharField(source="offer.title", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingPlan
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "candidate_email",
            "offer",
            "offer_title",
            "template",
            "template_name",
            "status",
            "start_date",
            "progress",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "candidate_email",
            "offer_title",
            "template_name",
            "progress",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_progress(self, obj):
        from apps.onboarding.services import plan_progress

        return plan_progress(obj)


class OnboardingPlanTaskSerializer(serializers.ModelSerializer):
    plan_candidate = serializers.CharField(source="plan.candidate.full_name", read_only=True)
    definition_title = serializers.CharField(source="definition.title", read_only=True)
    completed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingPlanTask
        fields = [
            "id",
            "plan",
            "plan_candidate",
            "definition",
            "definition_title",
            "title",
            "status",
            "due_date",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "notes",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "plan_candidate",
            "definition_title",
            "completed_at",
            "completed_by",
            "completed_by_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_completed_by_name(self, obj):
        if obj.completed_by_id:
            name = f"{obj.completed_by.first_name} {obj.completed_by.last_name}".strip()
            return name or obj.completed_by.email
        return None


class OnboardingDocumentSerializer(serializers.ModelSerializer):
    plan_candidate = serializers.CharField(source="plan.candidate.full_name", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingDocument
        fields = [
            "id",
            "plan",
            "plan_candidate",
            "name",
            "file",
            "status",
            "uploaded_by",
            "uploaded_by_name",
            "approved_by",
            "approved_by_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "plan_candidate",
            "status",
            "uploaded_by",
            "uploaded_by_name",
            "approved_by",
            "approved_by_name",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_uploaded_by_name(self, obj):
        return self._user_name(obj.uploaded_by)

    def get_approved_by_name(self, obj):
        return self._user_name(obj.approved_by)

    @staticmethod
    def _user_name(user):
        if user is None:
            return None
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email


class CreatePlanSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    offer_id = serializers.UUIDField(required=False, allow_null=True)
    template_id = serializers.UUIDField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)


class CreateTaskSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    definition_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    due_date = serializers.DateField(required=False, allow_null=True)


class BlockTaskSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CreateOnboardingDocumentSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    name = serializers.CharField()
    file = serializers.FileField(required=False, allow_null=True)
