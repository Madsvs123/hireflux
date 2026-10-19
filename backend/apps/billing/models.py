"""
Billing models: plans, subscriptions, invoices, payment methods,
payment transactions, and usage records.

``Plan`` is a platform catalog entity (not org-scoped); everything else is
tenant-scoped. Provider tokens are stored encrypted and never exposed.
"""
from django.conf import settings
from django.db import models

from apps.core.models import (
    AuditedModel,
    SoftDeleteManager,
    SoftDeleteModel,
    TenantModel,
    TimeStampedModel,
)


class Plan(TimeStampedModel, SoftDeleteModel, AuditedModel):
    """Platform pricing plan (global catalog, org-visible)."""

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        ANNUAL = "annual", "Annual"

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=64, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    price_per_month = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    currency = models.CharField(max_length=8, default="USD")
    billing_cycle = models.CharField(
        max_length=16, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    features = models.JSONField(default=list, blank=True)
    limits = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["price_per_month"]

    def __str__(self):
        return f"{self.name} ({self.currency} {self.price_per_month}/{self.billing_cycle})"


class Subscription(TenantModel, SoftDeleteModel, AuditedModel):
    """An organization's subscription to a plan."""

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions", db_index=True
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    trial_end = models.DateTimeField(null=True, blank=True)
    seats = models.PositiveIntegerField(default=1)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Internal state, e.g. pending_plan_id for end-of-period changes.",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization.name} → {self.plan.name} [{self.status}]"


class Invoice(TenantModel, SoftDeleteModel, AuditedModel):
    """An invoice issued to an organization."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        VOID = "void", "Void"
        UNCOLLECTIBLE = "uncollectible", "Uncollectible"

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=32, unique=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    issued_at = models.DateTimeField(null=True, blank=True, db_index=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    line_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {description, quantity, unit_price, amount} items.",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-issued_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-issued_at"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} ({self.status})"


class PaymentMethod(TenantModel, SoftDeleteModel, AuditedModel):
    """A stored payment method. The provider token is encrypted."""

    class Type(models.TextChoices):
        CARD = "card", "Card"
        BANK = "bank", "Bank"

    type = models.CharField(max_length=8, choices=Type.choices, default=Type.CARD)
    brand = models.CharField(max_length=32, blank=True, default="")
    last4 = models.CharField(max_length=4, blank=True, default="")
    exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_default = models.BooleanField(default=False, db_index=True)
    provider_token_encrypted = models.JSONField(
        default=dict,
        blank=True,
        help_text="Encrypted provider token (e.g. Stripe PaymentMethod id).",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.brand or self.type} •••• {self.last4}"


class PaymentTransaction(TenantModel, SoftDeleteModel, AuditedModel):
    """A single payment attempt or refund."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    provider = models.CharField(max_length=64, blank=True, default="mock")
    provider_ref = models.CharField(max_length=128, blank=True, default="", db_index=True)
    failure_reason = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.provider} {self.amount} {self.currency} [{self.status}]"


class UsageRecord(TenantModel, SoftDeleteModel, AuditedModel):
    """Aggregated usage metric for an organization (hourly bucket)."""

    class Metric(models.TextChoices):
        ACTIVE_JOBS = "active_jobs", "Active Jobs"
        CANDIDATES = "candidates", "Candidates"
        STORAGE = "storage", "Storage (MB)"
        API_CALLS = "api_calls", "API Calls"

    metric = models.CharField(max_length=32, choices=Metric.choices, db_index=True)
    quantity = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-recorded_at"]
        unique_together = [("organization", "metric", "recorded_at")]

    def __str__(self):
        return f"{self.metric}: {self.quantity} @ {self.recorded_at}"
