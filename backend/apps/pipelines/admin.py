"""
Django admin for pipelines domain.
"""
from django.contrib import admin

from apps.pipelines.models import (
    Application,
    ApplicationActivity,
    AutomatedTask,
    BulkActionLog,
    PipelineStage,
    PipelineTemplate,
    StageHistory,
)


class PipelineStageInline(admin.TabularInline):
    model = PipelineStage
    extra = 0
    fields = ("order", "name", "stage_type", "is_terminal", "auto_reject_days", "color")


@admin.register(PipelineTemplate)
class PipelineTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_default", "is_active", "created_at")
    list_filter = ("is_default", "is_active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)
    inlines = [PipelineStageInline]


@admin.register(PipelineStage)
class PipelineStageAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "stage_type", "order", "is_terminal")
    list_filter = ("stage_type", "is_terminal")
    raw_id_fields = ("organization", "template")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "stage",
        "status",
        "relevance_score",
        "knockout_failed",
        "applied_at",
    )
    list_filter = ("status", "knockout_failed")
    search_fields = ("candidate__email", "candidate__first_name", "job__titel")
    raw_id_fields = ("organization", "job", "candidate", "stage")


@admin.register(StageHistory)
class StageHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "from_stage", "to_stage", "moved_by", "created_at")
    raw_id_fields = ("organization", "application", "from_stage", "to_stage", "moved_by")


@admin.register(ApplicationActivity)
class ApplicationActivityAdmin(admin.ModelAdmin):
    list_display = ("application", "activity_type", "moved_by", "created_at")
    list_filter = ("activity_type",)
    raw_id_fields = ("organization", "application", "actor")


@admin.register(AutomatedTask)
class AutomatedTaskAdmin(admin.ModelAdmin):
    list_display = ("task_type", "application", "status", "created_at", "completed_at")
    list_filter = ("task_type", "status")
    raw_id_fields = ("organization", "application", "stage")


@admin.register(BulkActionLog)
class BulkActionLogAdmin(admin.ModelAdmin):
    list_display = ("action_type", "success_count", "failure_count", "created_by", "created_at")
    list_filter = ("action_type",)
    raw_id_fields = ("organization",)
