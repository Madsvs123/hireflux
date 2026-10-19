"""
Recruiting events: events, sessions, registrations, and tasks.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class RecruitingEvent(TenantModel, SoftDeleteModel, AuditedModel):
    """A recruiting event (career fair, webinar, campus event, ...)."""

    class EventType(models.TextChoices):
        CAREER_FAIR = "career_fair", "Career Fair"
        WEBINAR = "webinar", "Webinar"
        CAMPUS = "campus", "Campus"
        ONSITE = "onsite", "On-site"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=255)
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        default=EventType.OTHER,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    is_virtual = models.BooleanField(default=False)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    cover_image = models.ImageField(upload_to="events/covers/", null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["organization", "status", "start_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class EventSession(TenantModel, SoftDeleteModel, AuditedModel):
    """A session/agenda item within an event."""

    event = models.ForeignKey(
        RecruitingEvent,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    title = models.CharField(max_length=255)
    speaker = models.CharField(max_length=255, blank=True, default="")
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    room = models.CharField(max_length=128, blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["start_at", "created_at"]
        indexes = [
            models.Index(fields=["event", "start_at"]),
        ]

    def __str__(self):
        return f"{self.title} @ {self.event_id}"


class EventRegistration(TenantModel, SoftDeleteModel, AuditedModel):
    """A person registered for an event."""

    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        ATTENDED = "attended", "Attended"
        NO_SHOW = "no_show", "No Show"
        CANCELLED = "cancelled", "Cancelled"
        WAITLISTED = "waitlisted", "Waitlisted"

    event = models.ForeignKey(
        RecruitingEvent,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_registrations",
    )
    email = models.EmailField(db_index=True)
    first_name = models.CharField(max_length=120, blank=True, default="")
    last_name = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REGISTERED,
        db_index=True,
    )
    registered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-registered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "event", "email"],
                condition=models.Q(is_deleted=False),
                name="uniq_event_registration_email",
            )
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"{self.email} @ {self.event_id} [{self.status}]"


class EventTask(TenantModel, SoftDeleteModel, AuditedModel):
    """To-do associated with running an event."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(
        RecruitingEvent,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=255)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="event_tasks",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["due_at", "created_at"]
        indexes = [
            models.Index(fields=["event", "status"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"
