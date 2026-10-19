"""
Candidate profiles, education, experience, documents, notes, and duplicates.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class Candidate(TenantModel, SoftDeleteModel, AuditedModel):
    """Talent / applicant profile within an organization."""

    class Source(models.TextChoices):
        CAREER_PAGE = "career_page", "Career Page"
        REFERRAL = "referral", "Referral"
        AGENCY = "agency", "Agency"
        LINKEDIN = "linkedin", "LinkedIn"
        INDEED = "indeed", "Indeed"
        SOURCED = "sourced", "Sourced"
        IMPORT = "import", "Import"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_profiles",
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True, default="")
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=64, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    portfolio_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")
    website_url = models.URLField(blank=True, default="")
    headline = models.CharField(max_length=255, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.OTHER,
    )
    tags = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    years_experience = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    salary_expectation_min = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    salary_expectation_max = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    salary_currency = models.CharField(max_length=8, default="USD")
    is_talent_pool = models.BooleanField(default=False, db_index=True)
    do_not_hire = models.BooleanField(default=False, db_index=True)
    do_not_hire_reason = models.TextField(blank=True, default="")
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
    )
    custom_fields = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "last_name", "first_name"]),
            models.Index(fields=["organization", "is_talent_pool"]),
            models.Index(fields=["organization", "do_not_hire"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"],
                condition=models.Q(is_deleted=False, duplicate_of__isnull=False),
                name="uniq_active_candidate_email_per_org",
            )
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}".strip()

    @property
    def name(self):
        """Alias for full_name (spec: Candidate.name)."""
        return self.full_name


class CandidateEducation(TenantModel, AuditedModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="education")
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255, blank=True, default="")
    field_of_study = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")
    gpa = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        ordering = ["end_date", "-start_date"]

    def __str__(self):
        return f"{self.degree} @ {self.institution}"


class CandidateExperience(TenantModel, AuditedModel):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="experience")
    company = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, default="")
    skills_used = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-end_date", "-start_date"]
        verbose_name_plural = "candidate experiences"

    def __str__(self):
        return f"{self.title} @ {self.company}"


class CandidateCertification(TenantModel, AuditedModel):
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="certifications"
    )
    name = models.CharField(max_length=255)
    issuer = models.CharField(max_length=255, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=128, blank=True, default="")
    credential_url = models.URLField(blank=True, default="")

    class Meta:
        ordering = ["-issue_date"]

    def __str__(self):
        return self.name


class CandidateDocument(TenantModel, AuditedModel):
    class DocType(models.TextChoices):
        RESUME = "resume", "Resume"
        COVER_LETTER = "cover_letter", "Cover Letter"
        PORTFOLIO = "portfolio", "Portfolio"
        CERTIFICATE = "certificate", "Certificate"
        OTHER = "other", "Other"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=32, choices=DocType.choices, default=DocType.RESUME)
    title = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to="candidates/documents/%Y/%m/", blank=True)
    file_name = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=128, blank=True, default="")
    file_size = models.PositiveIntegerField(null=True, blank=True)
    parsed_text = models.TextField(blank=True, default="")
    parse_status = models.CharField(
        max_length=32,
        default="pending",
        help_text="pending|processing|completed|failed",
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or self.file_name or str(self.pk)


class CandidateNote(TenantModel, AuditedModel):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TEAM = "team", "Team"
        HIRING_TEAM = "hiring_team", "Hiring Team"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="notes")
    body = models.TextField()
    visibility = models.CharField(
        max_length=32,
        choices=Visibility.choices,
        default=Visibility.TEAM,
    )
    pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return f"Note on {self.candidate_id}"


class CommunicationLog(TenantModel, AuditedModel):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        CALL = "call", "Call"
        IN_APP = "in_app", "In-App"
        OTHER = "other", "Other"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="communications"
    )
    channel = models.CharField(max_length=16, choices=Channel.choices, default=Channel.EMAIL)
    direction = models.CharField(
        max_length=16, choices=Direction.choices, default=Direction.OUTBOUND
    )
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.channel} {self.direction} → {self.candidate_id}"


class DuplicateCandidateMatch(TenantModel, AuditedModel):
    class MatchType(models.TextChoices):
        EMAIL_EXACT = "email_exact", "Email Exact"
        NAME_PHONE = "name_phone", "Name + Phone Fuzzy"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        MERGED = "merged", "Merged"
        DISMISSED = "dismissed", "Dismissed"

    candidate_a = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="duplicate_matches_as_a"
    )
    candidate_b = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="duplicate_matches_as_b"
    )
    match_type = models.CharField(max_length=32, choices=MatchType.choices)
    confidence = models.FloatField(default=1.0)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    details = models.JSONField(default=dict, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_duplicate_matches",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "candidate_a", "candidate_b", "match_type")]

    def __str__(self):
        return f"{self.match_type}: {self.candidate_a_id} ↔ {self.candidate_b_id}"
