"""
Background check packages, requests, reports, disputes, and providers.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class BackgroundCheckPackage(TenantModel, SoftDeleteModel, AuditedModel):
    """A configurable bundle of background check types."""

    class CheckType(models.TextChoices):
        IDENTITY = "identity", "Identity"
        CRIMINAL = "criminal", "Criminal"
        EMPLOYMENT = "employment", "Employment"
        EDUCATION = "education", "Education"
        CREDIT = "credit", "Credit"
        DRUG = "drug", "Drug"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    check_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of check types, e.g. identity, criminal, employment",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    turnaround_days = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class ScreeningProvider(TenantModel, SoftDeleteModel, AuditedModel):
    """A background check provider connection (per organization)."""

    name = models.CharField(max_length=128)
    key = models.SlugField(
        max_length=64,
        unique=True,
        help_text="Stable identifier used in the provider webhook URL.",
    )
    api_endpoint = models.URLField(blank=True, default="")
    api_key_encrypted = models.TextField(
        blank=True,
        default="",
        help_text="Placeholder for an encrypted API credential.",
    )
    is_active = models.BooleanField(default=True)
    supported_checks = models.JSONField(default=list, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.key:
            base = slugify(self.name)[:48] or "provider"
            self.key = base
        super().save(*args, **kwargs)


class BackgroundCheckRequest(TenantModel, SoftDeleteModel, AuditedModel):
    """A background check run against a candidate."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        ON_HOLD = "on_hold", "On Hold"
        CANCELLED = "cancelled", "Cancelled"

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="background_check_requests",
        db_index=True,
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="background_check_requests",
    )
    package = models.ForeignKey(
        BackgroundCheckPackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_background_checks",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    provider = models.ForeignKey(
        ScreeningProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    provider_ref = models.CharField(max_length=128, blank=True, default="", db_index=True)
    candidate_email = models.EmailField(blank=True, default="")
    candidate_phone = models.CharField(max_length=64, blank=True, default="")
    consent_given_at = models.DateTimeField(null=True, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "provider_ref"]),
        ]

    def __str__(self):
        return f"Background check {self.status} for {self.candidate_id}"


class BackgroundCheckReport(TenantModel, SoftDeleteModel, AuditedModel):
    """Provider results for a background check request, pending human review."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEAR = "clear", "Clear"
        CONSIDER = "consider", "Consider"
        FLAGGED = "flagged", "Flagged"

    request = models.ForeignKey(
        BackgroundCheckRequest,
        on_delete=models.CASCADE,
        related_name="reports",
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    summary = models.TextField(blank=True, default="")
    findings = models.JSONField(
        default=list,
        blank=True,
        help_text="[{check, status, detail}] per check type",
    )
    report_file = models.FileField(
        upload_to="background_checks/reports/", null=True, blank=True
    )
    received_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_background_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "status"]),
        ]

    def __str__(self):
        return f"Report {self.status} for request {self.request_id}"


class CheckDispute(TenantModel, SoftDeleteModel, AuditedModel):
    """A candidate dispute against a background check report."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        UNDER_REVIEW = "under_review", "Under Review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    report = models.ForeignKey(
        BackgroundCheckReport,
        on_delete=models.CASCADE,
        related_name="disputes",
        db_index=True,
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="check_disputes",
    )
    reason = models.CharField(max_length=255)
    details = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    resolution = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_check_disputes",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Dispute {self.status}: {self.reason}"
