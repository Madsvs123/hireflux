"""
Serializers for knowledge base domain.
"""
from rest_framework import serializers

from apps.knowledge_base.models import (
    ArticleAttachment,
    ArticleVote,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeCategory,
    KnowledgeComment,
)


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    article_count = serializers.IntegerField(source="articles.count", read_only=True)

    class Meta:
        model = KnowledgeCategory
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "icon",
            "order",
            "is_active",
            "article_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "slug",
            "article_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class KnowledgeArticleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    published_by_name = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    vote_count = serializers.IntegerField(source="votes.count", read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = [
            "id",
            "organization",
            "category",
            "category_name",
            "title",
            "slug",
            "summary",
            "body_html",
            "status",
            "view_count",
            "published_at",
            "published_by",
            "published_by_name",
            "updated_by",
            "comment_count",
            "vote_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "category_name",
            "slug",
            "status",
            "view_count",
            "published_at",
            "published_by",
            "published_by_name",
            "updated_by",
            "comment_count",
            "vote_count",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_published_by_name(self, obj):
        user = obj.published_by
        if not user:
            return None
        full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        return full or getattr(user, "email", str(user.pk))


class KnowledgeArticleVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeArticleVersion
        fields = [
            "id",
            "organization",
            "article",
            "version_number",
            "title",
            "body_html",
            "change_note",
            "created_by",
            "created_by_name",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return None
        full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        return full or getattr(user, "email", str(user.pk))


class KnowledgeCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    article_title = serializers.CharField(source="article.title", read_only=True)

    class Meta:
        model = KnowledgeComment
        fields = [
            "id",
            "organization",
            "article",
            "article_title",
            "author",
            "author_name",
            "body",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "article_title",
            "author",
            "author_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        user = obj.author
        if not user:
            return None
        full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        return full or getattr(user, "email", str(user.pk))


class ArticleVoteSerializer(serializers.ModelSerializer):
    article_title = serializers.CharField(source="article.title", read_only=True)

    class Meta:
        model = ArticleVote
        fields = [
            "id",
            "organization",
            "article",
            "article_title",
            "user",
            "helpful",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "article_title",
            "user",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ArticleAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ArticleAttachment
        fields = [
            "id",
            "organization",
            "article",
            "name",
            "file",
            "size",
            "uploaded_by",
            "uploaded_by_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "size",
            "uploaded_by",
            "uploaded_by_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def get_uploaded_by_name(self, obj):
        user = obj.uploaded_by
        if not user:
            return None
        full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        return full or getattr(user, "email", str(user.pk))


class RestoreVersionSerializer(serializers.Serializer):
    version_id = serializers.UUIDField()


class DiffVersionsSerializer(serializers.Serializer):
    version_a = serializers.UUIDField()
    version_b = serializers.UUIDField()


class VoteToggleSerializer(serializers.Serializer):
    article_id = serializers.UUIDField()
    helpful = serializers.BooleanField()


class KnowledgeSearchSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, default="")
    category_id = serializers.UUIDField(required=False, allow_null=True)
