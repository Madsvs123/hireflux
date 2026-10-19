"""
Reporting models: definitions, runs, exports, dashboard widgets.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class ReportDefinition(TenantModel, SoftDeleteModel, AuditedModel):
    """A saved report configuration with optional schedule."""

    class ReportType(models.TextChoices):
        HIRES = "hires", "Hires"
        PIPELINE = "pipeline", "Pipeline"
        SOURCE = "source", "Source"
        TIME_TO_FILL = "time_to_fill", "Time to Fill"
        OFFER_ACCEPTANCE = "offer_acceptance", "Offer Acceptance"
        INTERVIEW = "interview", "Interview"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    report_type = models.CharField(
        max_length=32,
        choices=ReportType.choices,
        default=ReportType.HIRES,
        db_index=True,
    )
    params = models.JSONField(
        default=dict,
        blank=True,
        help_text="Report parameters (date range, job, filters)",
    )
    schedule_cron = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="cron expression, e.g. 0 9 * * 1",
    )
    schedule_enabled = models.BooleanField(default=False, db_index=True)
    is_public = models.BooleanField(default=False)
    last_run_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "report_type", "schedule_enabled"]),
        ]

    def __str__(self):
        return self.name


class ReportRun(TenantModel, SoftDeleteModel, AuditedModel):
    """A single execution of a report definition."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    definition = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name="runs",
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    params_snapshot = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_runs_triggered",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "definition", "-created_at"]),
            models.Index(fields=["organization", "status", "-created_at"]),
        ]

    def __str__(self):
        return f"ReportRun {self.definition_id} [{self.status}]"


class ReportExport(TenantModel, SoftDeleteModel, AuditedModel):
    """Generated export file for a completed report run."""

    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        PDF = "pdf", "PDF"

    run = models.ForeignKey(
        ReportRun,
        on_delete=models.CASCADE,
        related_name="exports",
        db_index=True,
    )
    format = models.CharField(
        max_length=8,
        choices=Format.choices,
        default=Format.CSV,
    )
    file = models.FileField(upload_to="report_exports/", blank=True, null=True)
    size = models.PositiveBigIntegerField(default=0)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.format} export for run {self.run_id}"


class DashboardWidget(TenantModel, SoftDeleteModel, AuditedModel):
    """Configurable widget card on the reporting dashboard."""

    class WidgetType(models.TextChoices):
        SUMMARY = "summary", "Summary"
        BAR = "bar", "Bar Chart"
        LINE = "line", "Line Chart"
        PIE = "pie", "Pie Chart"
        TABLE = "table", "Table"
        RECENT = "recent", "Recent Items"

    title = models.CharField(max_length=255)
    widget_type = models.CharField(
        max_length=16,
        choices=WidgetType.choices,
        default=WidgetType.SUMMARY,
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Widget-specific config (report_type, params, layout)",
    )
    position = models.PositiveIntegerField(default=0, db_index=True)
    is_visible = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["position", "title"]

    def __str__(self):
        return self.title
