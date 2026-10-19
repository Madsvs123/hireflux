"""
Knowledge base models: categories, articles, versions, comments, votes, attachments.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class KnowledgeCategory(TenantModel, SoftDeleteModel, AuditedModel):
    """Top-level grouping for knowledge articles."""

    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=160, db_index=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=64, blank=True, default="")
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["order", "name"]
        unique_together = [("organization", "slug")]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "category"
        super().save(*args, **kwargs)


class KnowledgeArticle(TenantModel, SoftDeleteModel, AuditedModel):
    """An internal wiki article."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        db_index=True,
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, db_index=True)
    summary = models.TextField(blank=True, default="")
    body_html = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles_published",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "slug")]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["organization", "category", "status"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title) or "article"
        super().save(*args, **kwargs)


class KnowledgeArticleVersion(TenantModel, SoftDeleteModel, AuditedModel):
    """Immutable snapshot of an article at a point in time."""

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="versions",
        db_index=True,
    )
    version_number = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255)
    body_html = models.TextField(blank=True, default="")
    change_note = models.CharField(max_length=512, blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-version_number"]
        unique_together = [("organization", "article", "version_number")]

    def __str__(self):
        return f"{self.article_id} v{self.version_number}"


class KnowledgeComment(TenantModel, SoftDeleteModel, AuditedModel):
    """A comment on an article."""

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="comments",
        db_index=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_comments",
    )
    body = models.TextField()

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author_id} on {self.article_id}"


class ArticleVote(TenantModel, SoftDeleteModel, AuditedModel):
    """Did this article help? One vote per user per article."""

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="votes",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="article_votes",
        db_index=True,
    )
    helpful = models.BooleanField(default=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "article", "user")]

    def __str__(self):
        return f"{'Helpful' if self.helpful else 'Not helpful'} on {self.article_id}"


class ArticleAttachment(TenantModel, SoftDeleteModel, AuditedModel):
    """A file attached to an article."""

    article = models.ForeignKey(
        KnowledgeArticle,
        on_delete=models.CASCADE,
        related_name="attachments",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="knowledge_attachments/")
    size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_attachments_uploaded",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
