"""
Talent pools, referrals, career pages, saved candidates, and job alerts.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class TalentPool(TenantModel, SoftDeleteModel, AuditedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class TalentPoolMember(TenantModel, AuditedModel):
    pool = models.ForeignKey(TalentPool, on_delete=models.CASCADE, related_name="members")
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="talent_pool_memberships"
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="talent_pool_adds",
    )
    notes = models.TextField(blank=True, default="")
    source_application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("pool", "candidate")]

    def __str__(self):
        return f"{self.candidate_id} in {self.pool_id}"


class Referral(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWING = "reviewing", "Reviewing"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_made",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="referrals",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
    )
    candidate_email = models.EmailField()
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    relationship = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    bonus_eligible = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "candidate_email"]),
        ]

    def __str__(self):
        return f"Referral {self.candidate_email} by {self.referrer_id}"


class CareerPage(TenantModel, SoftDeleteModel, AuditedModel):
    """Public careers site branding for an organization."""

    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    tagline = models.CharField(max_length=512, blank=True, default="")
    about = models.TextField(blank=True, default="")
    branding = models.JSONField(
        default=dict,
        blank=True,
        help_text="logo_url, primary_color, secondary_color, hero_image, custom_css, etc.",
    )
    social_links = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    custom_domain = models.CharField(max_length=255, blank=True, default="")
    seo = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.slug or str(self.organization_id)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or slugify(getattr(self.organization, "slug", "")) or "careers"
            slug = base
            n = 0
            while CareerPage.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class SavedCandidate(TenantModel, AuditedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_candidates",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )
    notes = models.TextField(blank=True, default="")
    folder = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("user", "candidate")]

    def __str__(self):
        return f"{self.user_id} saved {self.candidate_id}"


class JobAlert(TenantModel, AuditedModel):
    """Optional candidate job alert subscription."""

    email = models.EmailField(db_index=True)
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_alerts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_alerts",
    )
    query = models.CharField(max_length=255, blank=True, default="")
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="department, location, employment_type, remote_policy, etc.",
    )
    frequency = models.CharField(
        max_length=16,
        default="daily",
        help_text="daily|weekly|instant",
    )
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "email", "is_active"])]

    def __str__(self):
        return f"Alert {self.email}: {self.query}"
