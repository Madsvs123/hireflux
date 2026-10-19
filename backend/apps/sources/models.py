"""
Sourcing models: channels, campaigns, recipients, attribution.
"""
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class SourceChannel(TenantModel, SoftDeleteModel, AuditedModel):
    """A channel candidates can come from (job board, social, agency...)."""

    class ChannelType(models.TextChoices):
        JOB_BOARD = "job_board", "Job Board"
        SOCIAL = "social", "Social"
        AGENCY = "agency", "Agency"
        REFERRAL = "referral", "Referral"
        DIRECT = "direct", "Direct"
        OTHER = "other", "Other"

    name = models.CharField(max_length=128)
    channel_type = models.CharField(
        max_length=32,
        choices=ChannelType.choices,
        default=ChannelType.OTHER,
        db_index=True,
    )
    url = models.URLField(blank=True, default="")
    cost_per_post = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class SourcingCampaign(TenantModel, SoftDeleteModel, AuditedModel):
    """A targeted sourcing push through a channel to a job or talent pool."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=255)
    channel = models.ForeignKey(
        SourceChannel,
        on_delete=models.PROTECT,
        related_name="campaigns",
        db_index=True,
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sourcing_campaigns",
    )
    talent_pool = models.ForeignKey(
        "talent.TalentPool",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sourcing_campaigns",
    )
    goal = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["organization", "channel", "-created_at"]),
        ]

    def __str__(self):
        return self.name


class CampaignRecipient(TenantModel, SoftDeleteModel, AuditedModel):
    """An individual contact targeted by a sourcing campaign."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        OPENED = "opened", "Opened"
        REPLIED = "replied", "Replied"
        OPTED_OUT = "opted_out", "Opted Out"

    campaign = models.ForeignKey(
        SourcingCampaign,
        on_delete=models.CASCADE,
        related_name="recipients",
        db_index=True,
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaign_recipients",
    )
    email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "campaign", "email")]

    def __str__(self):
        return f"{self.email} [{self.status}]"


class CandidateSourceAttribution(TenantModel, SoftDeleteModel, AuditedModel):
    """Tracks which channel/campaign brought a candidate in."""

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="source_attributions",
        db_index=True,
    )
    channel = models.ForeignKey(
        SourceChannel,
        on_delete=models.PROTECT,
        related_name="attributions",
        db_index=True,
    )
    campaign = models.ForeignKey(
        SourcingCampaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attributions",
    )
    source_detail = models.CharField(max_length=255, blank=True, default="")
    attribution_date = models.DateField(default=timezone.now, db_index=True)
    utm_source = models.CharField(max_length=128, blank=True, default="")
    utm_medium = models.CharField(max_length=128, blank=True, default="")
    utm_campaign = models.CharField(max_length=128, blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-attribution_date"]
        unique_together = [("organization", "candidate", "channel", "attribution_date")]

    def __str__(self):
        return f"{self.candidate_id} via {self.channel_id}"
