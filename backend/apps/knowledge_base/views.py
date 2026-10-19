"""
Knowledge base ViewSets: categories, articles, versions, comments, votes, search.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.knowledge_base import services
from apps.knowledge_base.models import (
    ArticleAttachment,
    ArticleVote,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeCategory,
    KnowledgeComment,
)
from apps.knowledge_base.serializers import (
    ArticleAttachmentSerializer,
    ArticleVoteSerializer,
    DiffVersionsSerializer,
    KnowledgeArticleSerializer,
    KnowledgeArticleVersionSerializer,
    KnowledgeCategorySerializer,
    KnowledgeCommentSerializer,
    KnowledgeSearchSerializer,
    RestoreVersionSerializer,
    VoteToggleSerializer,
)


class KnowledgeCategoryViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = KnowledgeCategory.objects.all()
    serializer_class = KnowledgeCategorySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["knowledge.view"],
        "POST": ["knowledge.manage"],
        "PUT": ["knowledge.manage"],
        "PATCH": ["knowledge.manage"],
        "DELETE": ["knowledge.manage"],
    }
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug", "description"]
    ordering = ["order", "name"]
    audit_resource_type = "KnowledgeCategory"


class KnowledgeArticleViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = KnowledgeArticle.objects.select_related(
        "category", "published_by"
    ).prefetch_related("comments", "votes", "attachments")
    serializer_class = KnowledgeArticleSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["knowledge.view"],
        "POST": ["knowledge.manage"],
        "PUT": ["knowledge.manage"],
        "PATCH": ["knowledge.manage"],
        "DELETE": ["knowledge.manage"],
    }
    filterset_fields = ["category", "status", "published_by"]
    search_fields = ["title", "slug", "summary", "body_html"]
    ordering_fields = ["created_at", "published_at", "view_count", "title", "status"]
    ordering = ["-created_at"]
    audit_resource_type = "KnowledgeArticle"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        services.snapshot_article_version(
            serializer.instance, actor=self.request.user, change_note="Created"
        )

    def perform_update(self, serializer):
        previous = self.get_object()
        instance = serializer.save(updated_by=self.request.user)
        if (
            instance.title != previous.title
            and instance.body_html != previous.body_html
        ):
            services.snapshot_article_version(
                instance, actor=self.request.user, change_note="Updated"
            )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        article = self.get_object()
        article = services.publish_article(article, actor=request.user)
        return Response(KnowledgeArticleSerializer(article).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        article = self.get_object()
        article = services.archive_article(article, actor=request.user)
        return Response(KnowledgeArticleSerializer(article).data)

    @action(detail=True, methods=["post"], url_path="restore-version")
    def restore_version(self, request, pk=None):
        """Restore the article from a historical version."""
        article = self.get_object()
        ser = RestoreVersionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        version = (
            KnowledgeArticleVersion.objects.for_org(request.organization)
            .filter(article=article, pk=ser.validated_data["version_id"])
            .first()
        )
        if not version:
            return Response(
                {"detail": "Version not found."}, status=status.HTTP_404_NOT_FOUND
            )
        article = services.restore_version(article, version, actor=request.user)
        return Response(KnowledgeArticleSerializer(article).data)

    @action(detail=True, methods=["post"], url_path="increment-view")
    def increment_view(self, request, pk=None):
        """Atomically bump the view counter."""
        article = self.get_object()
        article = services.increment_view(article)
        return Response({"view_count": article.view_count})

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        """List all versions of this article (newest first)."""
        article = self.get_object()
        versions = KnowledgeArticleVersion.objects.filter(
            article=article, is_deleted=False
        ).order_by("-version_number")
        return Response(KnowledgeArticleVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=["post"])
    def diff(self, request, pk=None):
        """Unified diff between two versions of this article."""
        article = self.get_object()
        ser = DiffVersionsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        versions = {
            v.pk: v
            for v in KnowledgeArticleVersion.objects.for_org(request.organization).filter(
                article=article,
                pk__in=[
                    ser.validated_data["version_a"],
                    ser.validated_data["version_b"],
                ],
            )
        }
        if len(versions) != 2:
            return Response(
                {"detail": "Both versions must belong to this article."},
                status=status.HTTP_404_NOT_FOUND,
            )
        diff = services.diff_versions(
            versions[ser.validated_data["version_a"]],
            versions[ser.validated_data["version_b"]],
        )
        return Response(diff)


class KnowledgeCommentViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = KnowledgeComment.objects.select_related("article", "author")
    serializer_class = KnowledgeCommentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["knowledge.view"],
        "POST": ["knowledge.manage"],
        "PUT": ["knowledge.manage"],
        "PATCH": ["knowledge.manage"],
        "DELETE": ["knowledge.manage"],
    }
    filterset_fields = ["article", "author"]
    search_fields = ["body"]
    ordering = ["created_at"]
    audit_resource_type = "KnowledgeComment"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        if instance.author_id is None:
            instance.author = self.request.user
            instance.save(update_fields=["author", "updated_at"])


class ArticleVoteViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ArticleVote.objects.select_related("article", "user")
    serializer_class = ArticleVoteSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["knowledge.view"],
        "POST": ["knowledge.manage"],
        "PUT": ["knowledge.manage"],
        "PATCH": ["knowledge.manage"],
        "DELETE": ["knowledge.manage"],
    }
    filterset_fields = ["article", "user", "helpful"]
    ordering = ["-created_at"]
    audit_resource_type = "ArticleVote"

    def perform_create(self, serializer):
        # One vote per user per article: delegate to the toggle service
        # (creates, or flips the existing vote) to avoid IntegrityErrors.
        article = serializer.validated_data["article"]
        helpful = serializer.validated_data.get("helpful", True)
        vote, _created = services.toggle_vote(article, self.request.user, helpful)
        serializer.instance = vote

    @action(detail=False, methods=["post"])
    def toggle(self, request):
        """Create or flip the requesting user's vote on an article."""
        ser = VoteToggleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        article = (
            KnowledgeArticle.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["article_id"])
            .first()
        )
        if not article:
            return Response(
                {"detail": "Article not found."}, status=status.HTTP_404_NOT_FOUND
            )
        vote, created = services.toggle_vote(
            article, request.user, ser.validated_data["helpful"]
        )
        return Response(
            ArticleVoteSerializer(vote).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ArticleAttachmentViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ArticleAttachment.objects.select_related("article", "uploaded_by")
    serializer_class = ArticleAttachmentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["knowledge.view"],
        "POST": ["knowledge.manage"],
        "PUT": ["knowledge.manage"],
        "PATCH": ["knowledge.manage"],
        "DELETE": ["knowledge.manage"],
    }
    filterset_fields = ["article", "uploaded_by"]
    search_fields = ["name"]
    ordering = ["-created_at"]
    audit_resource_type = "ArticleAttachment"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        if instance.uploaded_by_id is None:
            instance.uploaded_by = self.request.user
        if instance.file and not instance.size:
            instance.size = instance.file.size or 0
        if instance.uploaded_by_id is not None or instance.size:
            instance.save(update_fields=["uploaded_by", "size", "updated_at"])


class KnowledgeSearchView(APIView):
    """Search across article title, summary, and body."""

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["knowledge.view"]

    def get(self, request):
        ser = KnowledgeSearchSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        results = services.search_articles(
            request.organization,
            ser.validated_data.get("q", ""),
            category_id=ser.validated_data.get("category_id"),
        )
        return Response(
            {
                "query": ser.validated_data.get("q", ""),
                "count": len(results),
                "results": KnowledgeArticleSerializer(results, many=True).data,
            }
        )
