"""
Organization, department, office, and hiring team models.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel, TimeStampedModel


class OrganizationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=False, is_deleted=False)


class OrganizationManager(models.Manager):
    def get_queryset(self):
        return OrganizationQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()


class Organization(TimeStampedModel, SoftDeleteModel):
    class OrgType(models.TextChoices):
        COMPANY = "company", "Company"
        AGENCY = "agency", "Agency"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    org_type = models.CharField(
        max_length=32,
        choices=OrgType.choices,
        default=OrgType.COMPANY,
        db_index=True,
    )
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    website = models.URLField(blank=True, default="")
    industry = models.CharField(max_length=128, blank=True, default="")
    size = models.CharField(max_length=64, blank=True, default="")
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = OrganizationManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["org_type", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "org"
            slug = base
            n = 1
            while (
                Organization.all_objects.filter(slug=slug)
                .exclude(pk=None)
                .exists()
            ):
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)


class Department(TimeStampedModel, SoftDeleteModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name", "parent")]
        indexes = [
            models.Index(fields=["organization", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization})"


class Office(TimeStampedModel, SoftDeleteModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="offices",
    )
    name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255, blank=True, default="")
    address_line2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    state = models.CharField(max_length=128, blank=True, default="")
    postal_code = models.CharField(max_length=32, blank=True, default="")
    country = models.CharField(max_length=64, blank=True, default="")
    timezone = models.CharField(max_length=64, blank=True, default="UTC")
    is_headquarters = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return f"{self.name} ({self.organization})"


class HiringTeam(TimeStampedModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="hiring_teams",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hiring_teams",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class HiringTeamMember(TimeStampedModel):
    class TeamRole(models.TextChoices):
        LEAD = "lead", "Lead"
        RECRUITER = "recruiter", "Recruiter"
        HIRING_MANAGER = "hiring_manager", "Hiring Manager"
        INTERVIEWER = "interviewer", "Interviewer"
        COORDINATOR = "coordinator", "Coordinator"
        MEMBER = "member", "Member"

    team = models.ForeignKey(
        HiringTeam,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hiring_team_memberships",
    )
    role = models.CharField(
        max_length=32,
        choices=TeamRole.choices,
        default=TeamRole.MEMBER,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("team", "user")]
        indexes = [
            models.Index(fields=["team", "role"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.team} ({self.role})"
