"""
Messaging threads and participants. Notifications live in apps.core.models.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, Notification, TenantModel

# Re-export for app-level discoverability (canonical table: core_notification)
__all__ = [
    "Notification",
    "MessageThread",
    "Message",
    "MessageParticipant",
]


class MessageThread(TenantModel, AuditedModel):
    class ThreadType(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        INTERNAL = "internal", "Internal"
        APPLICATION = "application", "Application"
        GENERAL = "general", "General"

    subject = models.CharField(max_length=255, blank=True, default="")
    thread_type = models.CharField(
        max_length=16,
        choices=ThreadType.choices,
        default=ThreadType.GENERAL,
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="message_threads",
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="message_threads",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_threads",
    )
    is_closed = models.BooleanField(default=False)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["last_message_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "-last_message_at"]),
            models.Index(fields=["organization", "candidate"]),
        ]

    def __str__(self):
        return self.subject or f"Thread {self.pk}"


class MessageParticipant(TenantModel):
    class Role(models.TextChoices):
        STAFF = "staff", "Staff"
        CANDIDATE = "candidate", "Candidate"
        SYSTEM = "system", "System"

    thread = models.ForeignKey(
        MessageThread, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_participations",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STAFF)
    last_read_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        unique_together = [("thread", "user")]

    def __str__(self):
        return f"{self.user_id} in {self.thread_id}"


class Message(TenantModel, AuditedModel):
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_messages",
    )
    body = models.TextField()
    body_html = models.TextField(blank=True, default="")
    attachments = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]

    def __str__(self):
        return f"Message in {self.thread_id}"
