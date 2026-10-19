"""
Django admin for background checks domain.
"""
from django.contrib import admin

from apps.background_checks.models import (
    BackgroundCheckPackage,
    BackgroundCheckReport,
    BackgroundCheckRequest,
    CheckDispute,
    ScreeningProvider,
)

AUDIT_READONLY = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(BackgroundCheckPackage)
class BackgroundCheckPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "price", "turnaround_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY


@admin.register(ScreeningProvider)
class ScreeningProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "organization", "is_active", "api_endpoint")
    list_filter = ("is_active",)
    search_fields = ("name", "key", "api_endpoint")
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY + ("key", "api_key_encrypted")


@admin.register(BackgroundCheckRequest)
class BackgroundCheckRequestAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "package",
        "status",
        "provider",
        "provider_ref",
        "submitted_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = (
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
        "provider_ref",
    )
    raw_id_fields = (
        "organization",
        "candidate",
        "job",
        "package",
        "provider",
        "initiated_by",
    )
    readonly_fields = AUDIT_READONLY + ("result_summary",)


@admin.register(BackgroundCheckReport)
class BackgroundCheckReportAdmin(admin.ModelAdmin):
    list_display = ("request", "status", "received_at", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("request__candidate__first_name", "request__candidate__last_name")
    raw_id_fields = ("organization", "request", "reviewed_by")
    readonly_fields = AUDIT_READONLY + ("findings", "report_file")


@admin.register(CheckDispute)
class CheckDisputeAdmin(admin.ModelAdmin):
    list_display = ("reason", "report", "candidate", "status", "resolved_by", "resolved_at")
    list_filter = ("status",)
    search_fields = ("reason", "details")
    raw_id_fields = ("organization", "report", "candidate", "resolved_by")
    readonly_fields = AUDIT_READONLY
