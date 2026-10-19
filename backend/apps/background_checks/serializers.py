"""
Serializers for background checks domain.
"""
from rest_framework import serializers

from apps.background_checks.models import (
    BackgroundCheckPackage,
    BackgroundCheckReport,
    BackgroundCheckRequest,
    CheckDispute,
    ScreeningProvider,
)


class BackgroundCheckPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackgroundCheckPackage
        fields = [
            "id",
            "name",
            "description",
            "check_types",
            "price",
            "turnaround_days",
            "is_active",
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

    def validate_check_types(self, value):
        valid = set(BackgroundCheckPackage.CheckType.values)
        for item in value or []:
            if item in valid:
                raise serializers.ValidationError(f"Unknown check type: {item}")
        return value


class ScreeningProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningProvider
        fields = [
            "id",
            "name",
            "key",
            "api_endpoint",
            "api_key_encrypted",
            "is_active",
            "supported_checks",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "key",
            "api_key_encrypted",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class BackgroundCheckRequestSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email_actual = serializers.EmailField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    package_name = serializers.CharField(source="package.name", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    latest_report = serializers.SerializerMethodField()

    class Meta:
        model = BackgroundCheckRequest
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "candidate_email_actual",
            "job",
            "job_title",
            "package",
            "package_name",
            "status",
            "initiated_by",
            "submitted_at",
            "completed_at",
            "provider",
            "provider_name",
            "provider_ref",
            "candidate_email",
            "candidate_phone",
            "consent_given_at",
            "result_summary",
            "latest_report",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "candidate_email_actual",
            "job_title",
            "package_name",
            "provider_name",
            "status",
            "initiated_by",
            "submitted_at",
            "completed_at",
            "provider_ref",
            "consent_given_at",
            "result_summary",
            "latest_report",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_latest_report(self, obj):
        report = obj.reports.order_by("created_at").first()
        if report is None:
            return None
        return {
            "id": str(report.pk),
            "status": report.status,
            "summary": report.summary,
            "findings": report.findings,
            "received_at": report.received_at,
            "reviewed_at": report.reviewed_at,
        }


class BackgroundCheckReportSerializer(serializers.ModelSerializer):
    request_candidate = serializers.CharField(
        source="request.candidate.full_name", read_only=True
    )
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BackgroundCheckReport
        fields = [
            "id",
            "request",
            "request_candidate",
            "status",
            "summary",
            "findings",
            "report_file",
            "received_at",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "request",
            "request_candidate",
            "report_file",
            "received_at",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by_id is None:
            return None
        name = f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip()
        return name or obj.reviewed_by.email


class CheckDisputeSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CheckDispute
        fields = [
            "id",
            "report",
            "candidate",
            "candidate_name",
            "reason",
            "details",
            "status",
            "resolution",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "status",
            "resolution",
            "resolved_by",
            "resolved_by_name",
            "resolved_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_resolved_by_name(self, obj):
        if obj.resolved_by_id is None:
            return None
        name = f"{obj.resolved_by.first_name} {obj.resolved_by.last_name}".strip()
        return name or obj.resolved_by.email


class CreateCheckRequestSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    job_id = serializers.UUIDField(required=False, allow_null=True)
    package_id = serializers.UUIDField(required=False, allow_null=True)
    candidate_email = serializers.EmailField(required=False, allow_blank=True, default="")
    candidate_phone = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewReportSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            BackgroundCheckReport.Status.CLEAR,
            BackgroundCheckReport.Status.CONSIDER,
            BackgroundCheckReport.Status.FLAGGED,
        ]
    )
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    findings = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )


class CreateDisputeSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    candidate_id = serializers.UUIDField()
    reason = serializers.CharField()
    details = serializers.CharField(required=False, allow_blank=True, default="")


class ResolveDisputeSerializer(serializers.Serializer):
    resolution = serializers.CharField(required=False, allow_blank=True, default="")
