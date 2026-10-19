"""
Interview scheduling: calendar accounts, availability rules, slots, links, bookings.
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class CalendarAccount(TenantModel, SoftDeleteModel, AuditedModel):
    """A connected calendar provider account for a staff user."""

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        OUTLOOK = "outlook", "Outlook"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_accounts",
    )
    provider = models.CharField(
        max_length=16,
        choices=Provider.choices,
        default=Provider.GOOGLE,
        db_index=True,
    )
    email = models.EmailField(db_index=True)
    access_token_encrypted = models.TextField(blank=True, default="")
    refresh_token_encrypted = models.TextField(blank=True, default="")
    calendar_id = models.CharField(max_length=255, blank=True, default="")
    is_primary = models.BooleanField(default=False, db_index=True)
    sync_enabled = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        unique_together = [("organization", "user", "provider", "email")]

    def __str__(self):
        return f"{self.provider} {self.email} ({self.user_id})"


class AvailabilityRule(TenantModel, SoftDeleteModel, AuditedModel):
    """Recurring availability window for a staff user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_rules",
    )
    title = models.CharField(max_length=128, blank=True, default="")
    days_of_week = models.JSONField(
        default=list,
        blank=True,
        help_text="List of weekday ints, 0=Monday ... 6=Sunday.",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    buffer_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["title", "start_time"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.title or self.user_id} {self.start_time}-{self.end_time}"


class InterviewSlot(TenantModel, SoftDeleteModel, AuditedModel):
    """A concrete interview time slot generated from availability rules."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        BOOKED = "booked", "Booked"
        HELD = "held", "Held"
        EXPIRED = "expired", "Expired"

    availability_rule = models.ForeignKey(
        AvailabilityRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slots",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_slots",
    )
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    held_until = models.DateTimeField(null=True, blank=True)
    booking_request = models.ForeignKey(
        "BookingRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slots",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["user", "start_at", "status"]),
        ]

    def __str__(self):
        return f"Slot {self.start_at}-{self.end_at} [{self.status}]"


class SchedulingLink(TenantModel, SoftDeleteModel, AuditedModel):
    """A public booking link pointing at a host's availability."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=160, db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheduling_links",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduling_links",
    )
    duration_minutes = models.PositiveIntegerField(default=60)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    availability_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="List of availability rule UUIDs used for this link.",
    )
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "slug")]
        indexes = [
            models.Index(fields=["organization", "owner", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:100] or "scheduling"
            candidate = f"{base}-1"
            n = 1
            while (
                SchedulingLink.all_objects.filter(
                    organization_id=self.organization_id, slug=candidate
                )
                .exclude(pk=self.pk)
                .exists()
            ):
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)


class BookingRequest(TenantModel, SoftDeleteModel, AuditedModel):
    """A requested (or confirmed) booking through a scheduling link."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        DECLINED = "declined", "Declined"

    scheduling_link = models.ForeignKey(
        SchedulingLink,
        on_delete=models.CASCADE,
        related_name="booking_requests",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_requests",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    requested_slot_start = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    confirmation_token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,
        default="",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    meeting_url = models.CharField(max_length=512, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["scheduling_link", "status"]),
        ]

    def __str__(self):
        return f"{self.email} @ {self.requested_slot_start} [{self.status}]"

    def save(self, *args, **kwargs):
        if not self.confirmation_token:
            self.confirmation_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)