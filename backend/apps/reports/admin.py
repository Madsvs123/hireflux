"""
Django admin for reports domain.
"""
from django.contrib import admin

from apps.reports.models import (
    DashboardWidget,
    ReportDefinition,
    ReportExport,
    ReportRun,
)


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "report_type",
        "schedule_enabled",
        "schedule_cron",
        "is_public",
        "last_run_at",
    )
    list_filter = ("report_type", "schedule_enabled", "is_public")
    search_fields = ("name", "description")
    raw_id_fields = ("organization",)
    readonly_fields = ("last_run_at", "created_by", "updated_by", "created_at", "updated_at")


@admin.register(ReportRun)
class ReportRunAdmin(admin.ModelAdmin):
    list_display = (
        "definition",
        "organization",
        "status",
        "triggered_by",
        "started_at",
        "finished_at",
    )
    list_filter = ("status",)
    search_fields = ("definition__name", "error")
    raw_id_fields = ("organization", "definition", "triggered_by")
    readonly_fields = (
        "params_snapshot",
        "result_summary",
        "error",
        "started_at",
        "finished_at",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )


@admin.register(ReportExport)
class ReportExportAdmin(admin.ModelAdmin):
    list_display = ("run", "organization", "format", "size", "created_at")
    list_filter = ("format",)
    raw_id_fields = ("organization", "run")
    readonly_fields = ("file", "size", "created_by", "updated_by", "created_at", "updated_at")


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "widget_type",
        "position",
        "is_visible",
    )
    list_filter = ("widget_type", "is_visible")
    search_fields = ("title",)
    raw_id_fields = ("organization",)
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
