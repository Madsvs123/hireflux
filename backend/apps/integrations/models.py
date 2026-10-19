"""
Third-party integration models: providers, connections, webhooks, API keys.

Sensitive fields (``credentials_encrypted``, ``secret``, ``key_hash``) are
stored encrypted or hashed and are never exposed through serializers.
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


class IntegrationProvider(TimeStampedModel, SoftDeleteModel, AuditedModel):
    """
    Catalog entry for a third-party provider (global, not org-scoped).

    ``config_schema`` describes provider-specific fields and endpoints,
    e.g. ``{"base_url": ..., "health_path": ..., "authorization_url": ...}``.
    """

    class Category(models.TextChoices):
        CALENDAR = "calendar", "Calendar"
        COMMUNICATION = "communication", "Communication"
        HRIS = "hris", "HRIS"
        ATS = "ats", "ATS"
        OTHER = "other", "Other"

    class AuthType(models.TextChoices):
        OAUTH2 = "oauth2", "OAuth2"
        API_KEY = "api_key", "API Key"
        NONE = "none", "None"

    key = models.SlugField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=128)
    category = models.CharField(
        max_length=32, choices=Category.choices, default=Category.OTHER, db_index=True
    )
    description = models.TextField(blank=True, default="")
    auth_type = models.CharField(
        max_length=16, choices=AuthType.choices, default=AuthType.NONE
    )
    config_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class IntegrationConnection(TenantModel, SoftDeleteModel, AuditedModel):
    """An org's live connection to an integration provider."""

    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        DISCONNECTED = "disconnected", "Disconnected"
        ERROR = "error", "Error"

    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="connections",
        db_index=True,
    )
    name = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DISCONNECTED, db_index=True
    )
    credentials_encrypted = models.JSONField(
        default=dict,
        blank=True,
        help_text="Encrypted credential values, keyed by credential name.",
    )
    config = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="integration_connections_connected",
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "provider", "name")]

    def __str__(self):
        return f"{self.name} ({self.provider.name}) [{self.status}]"


class IntegrationConfig(TenantModel, SoftDeleteModel, AuditedModel):
    """Key/value configuration attached to a connection."""

    connection = models.ForeignKey(
        IntegrationConnection,
        on_delete=models.CASCADE,
        related_name="configs",
        db_index=True,
    )
    key = models.CharField(max_length=128)
    value = models.JSONField(default=dict, blank=True)
    is_secret = models.BooleanField(default=False)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["key"]
        unique_together = [("connection", "key")]

    def __str__(self):
        return f"{self.connection.name} / {self.key}"


class WebhookEndpoint(TenantModel, SoftDeleteModel, AuditedModel):
    """Outbound webhook destination owned by an organization."""

    name = models.CharField(max_length=128)
    url = models.URLField(max_length=512)
    secret = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Encrypted HMAC signing secret — write-only via the API.",
    )
    events = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event names this endpoint should receive, e.g. candidate.created",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class WebhookDelivery(TenantModel, SoftDeleteModel, AuditedModel):
    """Append-only log of a single webhook dispatch attempt."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    endpoint = models.ForeignKey(
        WebhookEndpoint,
        on_delete=models.CASCADE,
        related_name="deliveries",
        db_index=True,
    )
    event = models.CharField(max_length=128, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    request_headers = models.JSONField(default=dict, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, default="")
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["endpoint", "-created_at"]),
        ]

    def __str__(self):
        return f"Delivery {self.event} [{self.status}] attempts={self.attempts}"


class ApiKey(TenantModel, SoftDeleteModel, AuditedModel):
    """Org-scoped API key. Only the prefix and hash are stored."""

    name = models.CharField(max_length=128)
    key_prefix = models.CharField(max_length=16, blank=True, default="")
    key_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    scopes = models.JSONField(
        default=list, blank=True, help_text="Permission codes granted to this key."
    )
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}…)"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone

        return timezone.now() <= self.expires_at
