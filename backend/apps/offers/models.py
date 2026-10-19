"""
Offer templates, offers, approval chains, and onboarding handoff.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class OfferTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    body_text = models.TextField(blank=True, default="")
    default_currency = models.CharField(max_length=8, default="USD")
    default_employment_type = models.CharField(max_length=64, blank=True, default="")
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="Supported merge variables e.g. candidate_name, salary",
    )
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class OfferApprovalChain(TenantModel, SoftDeleteModel, AuditedModel):
    """Ordered list of approver steps for offers."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    steps = models.JSONField(
        default=list,
        blank=True,
        help_text="[{order, role_name?, user_id?, label}]",
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class Offer(TenantModel, SoftDeleteModel, AuditedModel)
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED_INTERNAL = "rejected_internal", "Rejected (Internal)"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        WITHDRAWN = "withdrawn", "Withdrawn"

    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="offers",
    )
    template = models.ForeignKey(
        OfferTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    approval_chain = models.ForeignKey(
        OfferApprovalChain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="USD")
    equity = models.CharField(max_length=128, blank=True, default="")
    bonus = models.CharField(max_length=128, blank=True, default="")
    benefits = models.JSONField(default=list, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    employment_type = models.CharField(max_length=64, blank=True, default="")
    work_location = models.CharField(max_length=255, blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    body_text = models.TextField(blank=True, default="")
    current_approval_step = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    candidate_response_note = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
            models.Index(fields=["organization", "expires_at"]),
        ]

    def __str__(self):
        return self.title or f"Offer {self.pk}"


class OfferApproval(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SKIPPED = "skipped", "Skipped"

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="approvals")
    step_order = models.PositiveIntegerField(default=0)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offer_approvals",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    label = models.CharField(max_length=128, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-step_order", "created_at"]
        unique_together = [("offer", "approver")]

    def __str__(self):
        return f"Approval step {self.step_order} [{self.status}]"


class OnboardingHandoff(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    offer = models.OneToOneField(
        Offer, on_delete=models.CASCADE, related_name="onboarding_handoff"
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="onboarding_handoffs",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="onboarding_handoffs",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    start_date = models.DateField(null=True, blank=True)
    checklist = models.JSONField(
        default=list,
        blank=True,
        help_text="[{key, label, done, due_at?}]",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_assignments",
    )
    notes = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Onboarding {self.status} for {self.candidate_id}"
