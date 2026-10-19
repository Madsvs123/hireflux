"""
Serializers for reports domain.
"""
from rest_framework import serializers

from apps.reports.models import (
    DashboardWidget,
    ReportDefinition,
    ReportExport,
    ReportRun,
)


class ReportDefinitionSerializer(serializers.ModelSerializer):
    last_run_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "report_type",
            "params",
            "schedule_cron",
            "schedule_enabled",
            "is_public",
            "last_run_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "last_run_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ReportDefinitionPreviewSerializer(serializers.Serializer):
    params = serializers.JSONField(required=False, default=dict)


class ReportRunSerializer(serializers.ModelSerializer):
    definition_name = serializers.CharField(
        source="definition.description", read_only=True, default=None
    )
    report_type = serializers.CharField(source="definition.report_type", read_only=True)
    exports = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = ReportRun
        fields = [
            "id",
            "organization",
            "definition",
            "definition_name",
            "report_type",
            "status",
            "params_snapshot",
            "result_summary",
            "error",
            "started_at",
            "finished_at",
            "triggered_by",
            "created_by",
            "updated_by",
            "exports",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReportExportSerializer(serializers.ModelSerializer):
    run_status = serializers.CharField(source="run.status", read_only=True)
    definition_name = serializers.CharField(
        source="run.definition.name", read_only=True, default=None
    )

    class Meta:
        model = ReportExport
        fields = [
            "id",
            "organization",
            "run",
            "run_status",
            "definition_name",
            "format",
            "file",
            "size",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "run_status",
            "definition_name",
            "file",
            "size",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = [
            "id",
            "organization",
            "title",
            "widget_type",
            "config",
            "position",
            "is_visible",
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


class WidgetReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField())
