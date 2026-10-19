"""
Serializers for compliance domain.
"""
from rest_framework import serializers

from apps.compliance.models import (
    ComplianceNote,
    CompliancePolicy,
    ConsentRecord,
    DataExportRequest,
    DataRetentionPolicy,
    EEODeclaration,
)


class CompliancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompliancePolicy
        fields = [
            "id",
            "name",
            "policy_type",
            "version",
            "content_html",
            "is_active",
            "effective_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "is_active",
            "effective_at",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ConsentRecordSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ConsentRecord
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "user",
            "user_email",
            "policy",
            "policy_name",
            "purpose",
            "status",
            "granted_at",
            "withdrawn_at",
            "source",
            "ip_address",
            "consent_version",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "user_email",
            "policy_name",
            "status",
            "granted_at",
            "withdrawn_at",
            "consent_version",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class DataRetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DataRetentionPolicy
        fields = [
            "id",
            "data_type",
            "retention_days",
            "action",
            "is_active",
            "notes",
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


class EEODeclarationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = EEODeclaration
        fields = [
            "id",
            "token",
            "candidate",
            "candidate_name",
            "job",
            "job_title",
            "gender",
            "race_ethnicity",
            "veteran_status",
            "disability_status",
            "submitted_at",
            "is_anonymous",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "token",
            "candidate_name",
            "job_title",
            "submitted_at",
            "is_anonymous",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ComplianceNoteSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ComplianceNote
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "user",
            "user_email",
            "category",
            "body",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "user",
            "user_email",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class DataExportRequestSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)

    class Meta:
        model = DataExportRequest
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "requested_by",
            "requested_by_email",
            "status",
            "requested_at",
            "completed_at",
            "export_file",
            "include_fields",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate_name",
            "requested_by",
            "requested_by_email",
            "status",
            "requested_at",
            "completed_at",
            "export_file",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class GrantConsentSerializer(serializers.Serializer):
    policy_id = serializers.UUIDField()
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    candidate_id = serializers.UUIDField(required=False, allow_null=True)
    user_id = serializers.UUIDField(required=False, allow_null=True)
    source = serializers.CharField(required=False, allow_blank=True, default="")
    ip_address = serializers.IPAddressField(required=False, allow_null=True)


class SubmitEEOSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    gender = serializers.ChoiceField(
        choices=EEODeclaration.Gender.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    race_ethnicity = serializers.ChoiceField(
        choices=EEODeclaration.RaceEthnicity.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    veteran_status = serializers.ChoiceField(
        choices=EEODeclaration.VeteranStatus.choices,
        required=False,
        allow_blank=True,
        default="",
    )
    disability_status = serializers.ChoiceField(
        choices=EEODeclaration.DisabilityStatus.choices,
        required=False,
        allow_blank=True,
        default="",
    )


class CreateEEODeclarationSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField(required=False, allow_null=True)
    job_id = serializers.UUIDField(required=False, allow_null=True)


class CreateComplianceNoteSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.ChoiceField(
        choices=ComplianceNote.Category.choices,
        required=False,
        default=ComplianceNote.Category.OTHER,
    )
    body = serializers.CharField(required=False, allow_blank=True, default="")


class CreateExportRequestSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    include_fields = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
