"""
Compliance: policies, consents, retention, EEO declarations, notes, data exports.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class CompliancePolicy(TenantModel, SoftDeleteModel, AuditedModel):
    """A versioned compliance policy (privacy, consent, retention, EEO)."""

    class PolicyType(models.TextChoices):
        PRIVACY = "privacy", "Privacy"
        CONSENT = "consent", "Consent"
        RETENTION = "retention", "Retention"
        EEO = "eeo", "EEO"

    name = models.CharField(max_length=255)
    policy_type = models.CharField(
        max_length=16,
        choices=PolicyType.choices,
        default=PolicyType.PRIVACY,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    content_html = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=False, db_index=True)
    effective_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "name", "version")]

    def __str__(self):
        return f"{self.name} v{self.version}"


class ConsentRecord(TenantModel, AuditedModel):
    """A grant/withdrawal of consent against a consent policy."""

    class Status(models.TextChoices):
        GRANTED = "granted", "Granted"
        WITHDRAWN = "withdrawn", "Withdrawn"

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="consent_records",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="consent_records",
        db_index=True,
    )
    policy = models.ForeignKey(
        CompliancePolicy,
        on_delete=models.CASCADE,
        related_name="consent_records",
        db_index=True,
    )
    purpose = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.GRANTED,
        db_index=True,
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    consent_version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-granted_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["candidate", "policy"]),
        ]

    def __str__(self):
        return f"Consent {self.status}: {self.purpose}"


class DataRetentionPolicy(TenantModel, SoftDeleteModel, AuditedModel):
    """How long each data type is kept and what happens afterwards."""

    class DataType(models.TextChoices):
        CANDIDATES = "candidates", "Candidates"
        APPLICATIONS = "applications", "Applications"
        DOCUMENTS = "documents", "Documents"
        MESSAGES = "messages", "Messages"
        AUDIT_LOGS = "audit_logs", "Audit Logs"
        OFFERS = "offers", "Offers"
        INTERVIEWS = "interviews", "Interviews"
        ASSESSMENTS = "assessments", "Assessments"
        COMPLIANCE_NOTES = "compliance_notes", "Compliance Notes"
        CONSENT_RECORDS = "consent_records", "Consent Records"

    class Action(models.TextChoices):
        ANONYMIZE = "anonymize", "Anonymize"
        DELETE = "delete", "Delete"
        ARCHIVE = "archive", "Archive"

    data_type = models.CharField(
        max_length=32,
        choices=DataType.choices,
        db_index=True,
    )
    retention_days = models.PositiveIntegerField(default=365)
    action = models.CharField(
        max_length=16,
        choices=Action.choices,
        default=Action.DELETE,
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["data_type"]
        unique_together = [("organization", "data_type")]

    def __str__(self):
        return f"{self.data_type} → {self.action} after {self.retention_days}d"


class EEODeclaration(TenantModel, AuditedModel):
    """Self-identified EEO data, anonymous by default, token-based submission."""

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        NON_BINARY = "non_binary", "Non-binary"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class RaceEthnicity(models.TextChoices):
        AMERICAN_INDIAN = "american_indian", "American Indian or Alaska Native"
        ASIAN = "asian", "Asian"
        BLACK = "black", "Black or African American"
        HISPANIC = "hispanic", "Hispanic or Latino"
        PACIFIC_ISLANDER = "pacific_islander", "Native Hawaiian or Other Pacific Islander"
        WHITE = "white", "White"
        TWO_OR_MORE = "two_or_more", "Two or More Races"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class VeteranStatus(models.TextChoices):
        NOT_A_VETERAN = "not_a_veteran", "Not a veteran"
        VETERAN = "veteran", "Veteran"
        DISABLED_VETERAN = "disabled_veteran", "Disabled veteran"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class DisabilityStatus(models.TextChoices):
        NO_DISABILITY = "no_disability", "No disability"
        HAS_DISABILITY = "has_disability", "Has a disability"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    token = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eeo_declarations",
        db_index=True,
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eeo_declarations",
    )
    gender = models.CharField(
        max_length=32, choices=Gender.choices, blank=True, default=""
    )
    race_ethnicity = models.CharField(
        max_length=32, choices=RaceEthnicity.choices, blank=True, default=""
    )
    veteran_status = models.CharField(
        max_length=32, choices=VeteranStatus.choices, blank=True, default=""
    )
    disability_status = models.CharField(
        max_length=32, choices=DisabilityStatus.choices, blank=True, default=""
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        label = "anonymous" if self.is_anonymous else "identified"
        return f"EEO declaration {self.pk} ({label})"


class ComplianceNote(TenantModel, AuditedModel):
    """A note attached to a candidate or organization about compliance matters."""

    class Category(models.TextChoices):
        GDPR = "gdpr", "GDPR"
        EEO = "eeo", "EEO"
        RETENTION = "retention", "Retention"
        CONSENT = "consent", "Consent"
        OTHER = "other", "Other"

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="compliance_notes",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compliance_notes",
    )
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.OTHER,
    )
    body = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Compliance note [{self.category}]"


class DataExportRequest(TenantModel, SoftDeleteModel, AuditedModel):
    """A candidate data export request (GDPR data portability)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="data_export_requests",
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_export_requests",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    export_file = models.FileField(
        upload_to="compliance/exports/", null=True, blank=True
    )
    include_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Subset of candidate data to include; empty = everything.",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Export {self.status} for {self.candidate_id}"
