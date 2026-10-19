"""
Django admin for compliance domain.
"""
from django.contrib import admin

from apps.compliance.models import (
    ComplianceNote,
    CompliancePolicy,
    ConsentRecord,
    DataExportRequest,
    DataRetentionPolicy,
    EEODeclaration,
)

AUDIT_READONLY = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(CompliancePolicy)
class CompliancePolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "policy_type", "version", "is_active", "effective_at")
    list_filter = ("policy_type", "is_active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "user",
        "policy",
        "purpose",
        "status",
        "granted_at",
        "withdrawn_at",
    )
    list_filter = ("status",)
    search_fields = ("purpose", "candidate__first_name", "candidate__last_name")
    raw_id_fields = ("organization", "candidate", "user", "policy")
    readonly_fields = AUDIT_READONLY + ("consent_version",)


@admin.register(DataRetentionPolicy)
class DataRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ("data_type", "retention_days", "action", "is_active")
    list_filter = ("data_type", "action", "is_active")
    search_fields = ("data_type", "notes")
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY


@admin.register(EEODeclaration)
class EEODeclarationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "gender",
        "race_ethnicity",
        "veteran_status",
        "disability_status",
        "submitted_at",
        "is_anonymous",
    )
    list_filter = ("gender", "race_ethnicity", "veteran_status", "disability_status", "is_anonymous")
    search_fields = ("candidate__first_name", "candidate__last_name")
    raw_id_fields = ("organization", "candidate", "job")
    readonly_fields = AUDIT_READONLY + ("token",)


@admin.register(ComplianceNote)
class ComplianceNoteAdmin(admin.ModelAdmin):
    list_display = ("candidate", "user", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("body", "candidate__first_name", "candidate__last_name")
    raw_id_fields = ("organization", "candidate", "user")
    readonly_fields = AUDIT_READONLY


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "requested_by",
        "status",
        "requested_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("candidate__first_name", "candidate__last_name", "candidate__email")
    raw_id_fields = ("organization", "candidate", "requested_by")
    readonly_fields = AUDIT_READONLY + ("include_fields",)
