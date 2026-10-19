"""
Django admin for knowledge base domain.
"""
from django.contrib import admin

from apps.knowledge_base.models import (
    ArticleAttachment,
    ArticleVote,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeCategory,
    KnowledgeComment,
)


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    raw_id_fields = ("organization",)
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "category",
        "status",
        "view_count",
        "published_at",
    )
    list_filter = ("status", "category")
    search_fields = ("title", "slug", "summary", "body_html")
    raw_id_fields = ("organization", "category", "published_by")
    readonly_fields = (
        "view_count",
        "published_at",
        "published_by",
        "updated_by",
        "created_by",
        "created_at",
        "updated_at",
    )


@admin.register(KnowledgeArticleVersion)
class KnowledgeArticleVersionAdmin(admin.ModelAdmin):
    list_display = ("article", "version_number", "change_note", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "change_note")
    raw_id_fields = ("organization", "article")
    readonly_fields = (
        "version_number",
        "title",
        "body_html",
        "change_note",
        "created_by",
        "created_at",
    )


@admin.register(KnowledgeComment)
class KnowledgeCommentAdmin(admin.ModelAdmin):
    list_display = ("article", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("body",)
    raw_id_fields = ("organization", "article", "author")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(ArticleVote)
class ArticleVoteAdmin(admin.ModelAdmin):
    list_display = ("article", "user", "helpful", "created_at")
    list_filter = ("helpful",)
    raw_id_fields = ("organization", "article", "user")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(ArticleAttachment)
class ArticleAttachmentAdmin(admin.ModelAdmin):
    list_display = ("name", "article", "size", "uploaded_by", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("organization", "article", "uploaded_by")
    readonly_fields = ("size", "uploaded_by", "created_by", "updated_by", "created_at", "updated_at")
