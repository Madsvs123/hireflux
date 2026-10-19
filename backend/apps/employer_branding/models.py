"""
Employer branding: brand profile, careers site, team, testimonials, culture posts.
"""
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class BrandProfile(TenantModel, SoftDeleteModel, AuditedModel):
    """One-to-one brand identity used by the public careers site."""

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="brand_profile",
    )
    primary_color = models.CharField(max_length=16, default="#2563EB")
    secondary_color = models.CharField(max_length=16, default="#0F172A")
    logo = models.ImageField(upload_to="branding/logos/", null=True, blank=True)
    tagline = models.CharField(max_length=255, blank=True, default="")
    about_html = models.TextField(blank=True, default="")
    culture_values = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"BrandProfile {self.organization_id}"


class CareerSiteConfig(TenantModel, SoftDeleteModel, AuditedModel):
    """Careers site configuration (one per organization)."""

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="career_site_config",
    )
    site_name = models.CharField(max_length=128, default="Careers")
    slug = models.SlugField(max_length=160, db_index=True)
    enabled = models.BooleanField(default=False, db_index=True)
    hero_title = models.CharField(max_length=255, blank=True, default="")
    hero_subtitle = models.CharField(max_length=512, blank=True, default="")
    hero_image = models.ImageField(upload_to="branding/hero/", null=True, blank=True)
    footer_text = models.CharField(max_length=512, blank=True, default="")
    custom_css = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-updated_at"]
        unique_together = [("organization", "slug")]

    def __str__(self):
        return f"{self.site_name} ({self.slug})"


class TeamPage(TenantModel, SoftDeleteModel, AuditedModel):
    """Team member profile shown on the careers site."""

    name = models.CharField(max_length=128)
    role = models.CharField(max_length=128, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    photo = models.ImageField(upload_to="branding/team/", null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Testimonial(TenantModel, SoftDeleteModel, AuditedModel):
    """Candidate / employee testimonial shown on the careers site."""

    author_name = models.CharField(max_length=128)
    author_role = models.CharField(max_length=128, blank=True, default="")
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.author_name}: {self.content[:60]}"


class CulturePost(TenantModel, SoftDeleteModel, AuditedModel):
    """Life-at-company post for the careers site blog section."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255)
    body_html = models.TextField(blank=True, default="")
    cover_image = models.ImageField(upload_to="branding/culture/", null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PUBLISHED,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title
