"""
Interview kits, panels, scheduling, scorecards, and decision summaries.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class InterviewKit(TenantModel, SoftDeleteModel, AuditedModel):
    """Reusable interview guide with questions and score dimensions."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    questions = models.JSONField(
        default=list,
        blank=True,
        help_text="[{id, prompt, competency, expected_signals}]",
    )
    score_dimensions = models.JSONField(
        default=list,
        blank=True,
        help_text="[{key, label, weight, max_score}]",
    )
    duration_minutes = models.PositiveIntegerField(default=45)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class InterviewPanel(TenantModel, SoftDeleteModel, AuditedModel):
    """Named panel of interviewers."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="interview_panels",
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class Interview(TenantModel, SoftDeleteModel, AuditedModel):
    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone"
        VIDEO = "video", "Video"
        ONSITE = "onsite", "On-site"
        PANEL = "panel", "Panel"
        TECHNICAL = "technical", "Technical"
        BEHAVIORAL = "behavioral", "Behavioral"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"
        RESCHEDULED = "rescheduled", "Rescheduled"

    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    kit = models.ForeignKey(
        InterviewKit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    panel = models.ForeignKey(
        InterviewPanel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    interview_type = models.CharField(
        max_length=32,
        choices=InterviewType.choices,
        default=InterviewType.VIDEO,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    location = models.CharField(max_length=512, blank=True, default="")
    meeting_url = models.URLField(blank=True, default="")
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField(db_index=True)
    timezone = models.CharField(max_length=64, default="UTC")
    notes = models.TextField(blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["scheduled_start"]
        indexes = [
            models.Index(fields=["organization", "scheduled_start", "scheduled_end"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self):
        return self.title or f"Interview {self.pk}"


class InterviewerAssignment(TenantModel, AuditedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        PANELIST = "panelist", "Panelist"
        OBSERVER = "observer", "Observer"

    class ResponseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="assignments"
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_assignments",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PANELIST)
    response_status = models.CharField(
        max_length=16,
        choices=ResponseStatus.choices,
        default=ResponseStatus.PENDING,
    )
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]
        unique_together = [("interview", "interviewer")]

    def __str__(self):
        return f"{self.interviewer_id} @ {self.interview_id}"


class InterviewerAvailability(TenantModel, AuditedModel):
    """Recurring or one-off availability windows for an interviewer."""

    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_availability",
    )
    start = models.DateTimeField(db_index=True)
    end = models.DateTimeField(db_index=True)
    timezone = models.CharField(max_length=64, default="UTC")
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional RRULE-style string for recurring windows.",
    )
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["start"]
        verbose_name_plural = "interviewer availabilities"
        indexes = [
            models.Index(fields=["organization", "interviewer", "start", "end"]),
        ]

    def __str__(self):
        return f"{self.interviewer_id}: {self.start} → {self.end}"


class Scorecard(TenantModel, AuditedModel):
    class Recommendation(models.TextChoices):
        STRONG_YES = "strong_yes", "Strong Yes"
        YES = "yes", "Yes"
        NEUTRAL = "neutral", "Neutral"
        NO = "no", "No"
        STRONG_NO = "strong_no", "Strong No"

    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="scorecards"
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scorecards",
    )
    assignment = models.ForeignKey(
        InterviewerAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scorecards",
    )
    scores = models.JSONField(
        default=dict,
        blank=True,
        help_text="{dimension_key: {score, notes}}",
    )
    overall_score = models.FloatField(null=True, blank=True)
    recommendation = models.CharField(
        max_length=16,
        choices=Recommendation.choices,
        default=Recommendation.NEUTRAL,
    )
    strengths = models.TextField(blank=True, default="")
    concerns = models.TextField(blank=True, default="")
    private_notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("interview", "interviewer")]

    def __str__(self):
        return f"Scorecard {self.interviewer_id} → {self.interview_id}"


class InterviewDecisionSummary(TenantModel, AuditedModel):
    class Decision(models.TextChoices):
        ADVANCE = "advance", "Advance"
        HOLD = "hold", "Hold"
        REJECT = "reject", "Reject"
        PENDING = "pending", "Pending"

    interview = models.OneToOneField(
        Interview, on_delete=models.CASCADE, related_name="decision_summary"
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="interview_decisions",
    )
    decision = models.CharField(
        max_length=16,
        choices=Decision.choices,
        default=Decision.PENDING,
        db_index=True,
    )
    average_score = models.FloatField(null=True, blank=True)
    recommendation_tally = models.JSONField(default=dict, blank=True)
    scorecard_count = models.PositiveIntegerField(default=0)
    summary = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "interview decision summaries"

    def __str__(self):
        return f"Decision {self.decision} for {self.interview_id}"
