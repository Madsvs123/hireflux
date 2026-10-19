"""
Hiring pipelines, applications, stage history, activities, and automations.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class PipelineTemplate(TenantModel, SoftDeleteModel, AuditedModel)
    """Reusable pipeline definition for jobs."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class PipelineStage(TenantModel, AuditedModel):
    class StageType(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        ASSESSMENT = "assessment", "Assessment"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        TALENT_POOL = "talent_pool", "Talent Pool"
        CUSTOM = "custom", "Custom"

    template = models.ForeignKey(
        PipelineTemplate, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(max_length=128)
    stage_type = models.CharField(
        max_length=32,
        choices=StageType.choices,
        default=StageType.CUSTOM,
        db_index=True,
    )
    order = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=32, blank=True, default="#6B7280")
    is_terminal = models.BooleanField(default=False)
    auto_reject_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Auto-reject applications sitting in this stage longer than N days.",
    )
    allowed_next_stage_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Optional list of stage UUIDs that may follow this stage. Empty = any.",
    )
    automation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="e.g. {notify: true, create_task: 'schedule_interview', screen: true}",
    )

    class Meta:
        ordering = ["-order", "created_at"]
        unique_together = [("template", "name")]
        indexes = [
            models.Index(fields=["template", "order"]),
            models.Index(fields=["template", "stage_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.stage_type})"


class Application(TenantModel, SoftDeleteModel, AuditedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        TALENT_POOL = "talent_pool", "Talent Pool"

    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="applications"
    )
    stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    relevance_score = models.FloatField(null=True, blank=True, db_index=True)
    answers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map of screening_question_id → answer payload",
    )
    knockout_failed = models.BooleanField(default=False)
    source = models.CharField(max_length=64, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    stage_entered_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    hired_at = models.DateTimeField(null=True, blank=True)
    cover_letter = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["applied_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "job", "candidate"],
                condition=models.Q(is_deleted=False),
                name="uniq_org_job_candidate_application",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "job", "stage"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "-relevance_score"]),
            models.Index(fields=["stage", "stage_entered_at"]),
        ]

    def __str__(self):
        return f"App {self.candidate_id} → {self.job_id}"


class StageHistory(TenantModel):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="stage_history"
    )
    from_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    to_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stage_moves",
    )
    note = models.TextField(blank=True, default="")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_stage_id} → {self.to_stage_id}"


class ApplicationActivity(TenantModel):
    class ActivityType(models.TextChoices):
        CREATED = "created", "Created"
        STAGE_MOVE = "stage_move", "Stage Move"
        NOTE = "note", "Note"
        EMAIL = "email", "Email"
        SCORE = "score", "Score"
        TAG = "tag", "Tag"
        REJECT = "reject", "Reject"
        HIRE = "hire", "Hire"
        AUTOMATION = "automation", "Automation"
        BULK = "bulk", "Bulk Action"
        OTHER = "other", "Other"

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="activities"
    )
    activity_type = models.CharField(max_length=32, choices=ActivityType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application_activities",
    )
    message = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "application activities"

    def __str__(self):
        return f"{self.activity_type} on {self.application_id}"


class AutomatedTask(TenantModel, AuditedModel):
    class TaskType(models.TextChoices):
        NOTIFY = "notify", "Notify"
        EMAIL = "email", "Email"
        SCREEN = "screen", "Screen"
        SCHEDULE_INTERVIEW = "schedule_interview", "Schedule Interview"
        CREATE_ASSESSMENT = "create_assessment", "Create Assessment"
        AUTO_REJECT = "auto_reject", "Auto Reject"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="automated_tasks"
    )
    stage = models.ForeignKey(
        PipelineStage, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    task_type = models.CharField(max_length=32, choices=TaskType.choices)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_type} [{self.status}]"


class BulkActionLog(TenantModel, AuditedModel):
    class ActionType(models.TextChoices):
        MOVE = "move", "Move"
        REJECT = "reject", "Reject"
        TAG = "tag", "Tag"
        OTHER = "other", "Other"

    action_type = models.CharField(max_length=16, choices=ActionType.choices)
    application_ids = models.JSONField(default=list)
    payload = models.JSONField(default=dict, blank=True)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bulk {self.action_type}: {self.success_count} ok / {self.failure_count} fail"
