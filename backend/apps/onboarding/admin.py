"""
Django admin for onboarding domain.
"""
from django.contrib import admin

from apps.onboarding.models import (
    OnboardingDocument,
    OnboardingPlan,
    OnboardingPlanTask,
    OnboardingTaskDefinition,
    OnboardingTemplate,
)

AUDIT_READONLY = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    raw_id_fields = ("organization",)
    readonly_fields = AUDIT_READONLY


@admin.register(OnboardingTaskDefinition)
class OnboardingTaskDefinitionAdmin(admin.ModelAdmin):
    list_display = ("title", "template", "order", "required", "due_offset_days")
    list_filter = ("required",)
    search_fields = ("title", "description", "owner_role")
    raw_id_fields = ("organization", "template")
    readonly_fields = AUDIT_READONLY


@admin.register(OnboardingPlan)
class OnboardingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "offer",
        "template",
        "status",
        "start_date",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("candidate__first_name", "candidate__last_name", "candidate__email")
    raw_id_fields = ("organization", "candidate", "offer", "template")
    readonly_fields = AUDIT_READONLY


@admin.register(OnboardingPlanTask)
class OnboardingPlanTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "plan", "status", "due_date", "completed_at", "completed_by")
    list_filter = ("status",)
    search_fields = ("title", "notes")
    raw_id_fields = ("organization", "plan", "definition", "completed_by")
    readonly_fields = AUDIT_READONLY


@admin.register(OnboardingDocument)
class OnboardingDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "status", "uploaded_by", "approved_by", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)
    raw_id_fields = ("organization", "plan", "uploaded_by", "approved_by")
    readonly_fields = AUDIT_READONLY
