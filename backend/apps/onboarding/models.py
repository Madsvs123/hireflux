"""
New-hire onboarding: templates, task definitions, plans, plan tasks, documents.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class OnboardingTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    """Reusable checklist template for new-hire onboarding."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra template configuration, e.g. default assignee role.",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class OnboardingTaskDefinition(TenantModel, SoftDeleteModel, AuditedModel):
    """A single task definition belonging to an onboarding template."""

    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.CASCADE,
        related_name="task_definitions",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    owner_role = models.CharField(max_length=128, blank=True, default="")
    due_offset_days = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["order", "created_at"]
        unique_together = [("template", "order")]

    def __str__(self):
        return f"{self.title} ({self.template.name})"


class OnboardingPlan(TenantModel, SoftDeleteModel, AuditedModel):
    """A concrete onboarding plan for a hired candidate."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="onboarding_plans",
        db_index=True,
    )
    offer = models.ForeignKey(
        "offers.Offer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_plans",
        db_index=True,
    )
    template = models.ForeignKey(
        OnboardingTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plans",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    start_date = models.DateField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Onboarding {self.status} for {self.candidate_id}"


class OnboardingPlanTask(TenantModel, SoftDeleteModel, AuditedModel):
    """A concrete task on an onboarding plan."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        BLOCKED = "blocked", "Blocked"

    plan = models.ForeignKey(
        OnboardingPlan,
        on_delete=models.CASCADE,
        related_name="tasks",
        db_index=True,
    )
    definition = models.ForeignKey(
        OnboardingTaskDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plan_tasks",
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_onboarding_tasks",
    )
    notes = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["due_date", "created_at"]
        indexes = [
            models.Index(fields=["plan", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"


class OnboardingDocument(TenantModel, SoftDeleteModel, AuditedModel):
    """A document attached to an onboarding plan (paperwork, ID, contracts...)."""

    class Status(models.TextChoices):
        MISSING = "missing", "Missing"
        UPLOADED = "uploaded", "Uploaded"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    plan = models.ForeignKey(
        OnboardingPlan,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="onboarding/documents/", blank=True, null=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.MISSING,
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_onboarding_documents",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_onboarding_documents",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["plan", "status"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.status}]"
