"""
Serializers for pipelines domain.
"""
from rest_framework import serializers

from apps.pipelines.models import (
    Application,
    ApplicationActivity,
    AutomatedTask,
    BulkActionLog,
    PipelineStage,
    PipelineTemplate,
    StageHistory,
)


class PipelineStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PipelineStage
        fields = [
            "id",
            "template",
            "name",
            "stage_type",
            "order",
            "color",
            "is_terminal",
            "auto_reject_days",
            "allowed_next_stage_ids",
            "automation_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "template", "created_at", "updated_at"]


class PipelineTemplateSerializer(serializers.ModelSerializer):
    stages = PipelineStageSerializer(many=True, read_only=True)

    class Meta:
        model = PipelineTemplate
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "stages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "stages"]


class StageHistorySerializer(serializers.ModelSerializer):
    from_stage_name = serializers.CharField(source="from_stage.name", read_only=True, default=None)
    to_stage_name = serializers.CharField(source="to_stage.name", read_only=True, default=None)

    class Meta:
        model = StageHistory
        fields = [
            "id",
            "application",
            "from_stage",
            "to_stage",
            "from_stage_name",
            "to_stage_name",
            "moved_by",
            "note",
            "duration_seconds",
            "created_at",
        ]
        read_only_fields = fields


class ApplicationActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationActivity
        fields = [
            "id",
            "application",
            "activity_type",
            "actor",
            "message",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class AutomatedTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomatedTask
        fields = [
            "id",
            "application",
            "stage",
            "task_type",
            "status",
            "payload",
            "result",
            "error",
            "scheduled_for",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BulkActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkActionLog
        fields = [
            "id",
            "action_type",
            "application_ids",
            "payload",
            "success_count",
            "failure_count",
            "errors",
            "created_by",
            "created_at",
        ]
        read_only_fields = fields


class ApplicationListSerializer(serializers.ModelSerializer)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    stage_name = serializers.CharField(source="stage.stage_type", read_only=True, default=None)
    stage_type = serializers.CharField(source="stage.stage_type", read_only=True, default=None)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "job_title",
            "candidate",
            "candidate_name",
            "candidate_email",
            "stage",
            "stage_name",
            "stage_type",
            "status",
            "relevance_score",
            "knockout_failed",
            "tags",
            "applied_at",
            "stage_entered_at",
            "created_at",
        ]


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    stage_history = StageHistorySerializer(many=True, read_only=True)
    activities = ApplicationActivitySerializer(many=False, read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "job_title",
            "candidate",
            "candidate_name",
            "candidate_email",
            "stage",
            "status",
            "relevance_score",
            "answers",
            "knockout_failed",
            "source",
            "tags",
            "applied_at",
            "stage_entered_at",
            "rejected_at",
            "rejection_reason",
            "hired_at",
            "cover_letter",
            "metadata",
            "stage_history",
            "activities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "relevance_score",
            "knockout_failed",
            "applied_at",
            "stage_entered_at",
            "rejected_at",
            "hired_at",
            "stage_history",
            "activities",
            "created_at",
            "updated_at",
        ]


class ApplyToJobSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    candidate_id = serializers.UUIDField()
    answers = serializers.DictField(required=False, default=dict)
    cover_letter = serializers.CharField(required=False, allow_blank=True, default="")
    source = serializers.CharField(required=False, allow_blank=True, default="")


class MoveApplicationSerializer(serializers.Serializer):
    stage_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


class BulkMoveSerializer(serializers.Serializer):
    application_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    stage_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class BulkRejectSerializer(serializers.Serializer):
    application_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    stage_id = serializers.UUIDField(required=False, allow_null=True)


class BulkTagSerializer(serializers.Serializer):
    application_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    tags = serializers.ListField(child=serializers.CharField(max_length=64), min_length=1)
    mode = serializers.ChoiceField(choices=["add", "set", "remove"], default="add")


class BoardApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)
    headline = serializers.CharField(source="candidate.headline", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "candidate_email",
            "headline",
            "relevance_score",
            "status",
            "tags",
            "applied_at",
            "stage_entered_at",
            "knockout_failed",
        ]
