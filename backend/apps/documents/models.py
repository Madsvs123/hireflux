"""
Document templates, generated documents, and e-sign requests.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class DocumentCategory(TenantModel, SoftDeleteModel, AuditedModel):
    """A category used to organize document templates."""

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class DocumentTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    """Reusable document template with merge variables."""

    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    body_text = models.TextField(blank=True, default="")
    variables = models.JSONField(
        default=list,
        blank=True,
        help_text="Supported merge variables, e.g. candidate_name, offer_salary",
    )
    default_currency = models.CharField(max_length=8, default="USD")
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class GeneratedDocument(TenantModel, SoftDeleteModel, AuditedModel):
    """A concrete document generated from a template (or ad-hoc)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"
        VOID = "void", "Void"

    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
    )
    title = models.CharField(max_length=255)
    content_html = models.TextField(blank=True, default="")
    content_text = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    related_candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
        db_index=True,
    )
    related_job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
    )
    related_offer = models.ForeignKey(
        "offers.Offer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_documents",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.title


class DocumentSignRequest(TenantModel, SoftDeleteModel, AuditedModel):
    """An e-sign request sent to a signer for a generated document."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SIGNED = "signed", "Signed"
        DECLINED = "declined", "Declined"
        VOIDED = "voided", "Voided"

    token = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    document = models.ForeignKey(
        GeneratedDocument,
        on_delete=models.CASCADE,
        related_name="sign_requests",
        db_index=True,
    )
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    message = models.TextField(blank=True, default="")
    signed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    signature_data = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["signer_email", "status"]),
        ]

    def __str__(self):
        return f"Sign {self.signer_email} — {self.document.title}"


class DocumentSignature(TenantModel, AuditedModel):
    """An individual signature captured against a sign request."""

    sign_request = models.ForeignKey(
        DocumentSignRequest,
        on_delete=models.CASCADE,
        related_name="signatures",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    signature_svg = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_at"]
        unique_together = [("sign_request", "email")]

    def __str__(self)
        return f"Signature by {self.name} <{self.email}>"
