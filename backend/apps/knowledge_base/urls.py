"""
Knowledge base URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.knowledge_base.views import (
    ArticleAttachmentViewSet,
    ArticleVoteViewSet,
    KnowledgeArticleViewSet,
    KnowledgeCategoryViewSet,
    KnowledgeCommentViewSet,
    KnowledgeSearchView,
)

router = DefaultRouter()
router.register(r"knowledge-categories", KnowledgeCategoryViewSet, basename="knowledge-category")
router.register(r"knowledge-articles", KnowledgeArticleViewSet, basename="knowledge-article")
router.register(r"knowledge-comments", KnowledgeCommentViewSet, basename="knowledge-comment")
router.register(r"article-votes", ArticleVoteViewSet, basename="article-vote")
router.register(r"article-attachments", ArticleAttachmentViewSet, basename="article-attachment")

urlpatterns = [
    path("", include(router.urls)),
    path("knowledge-search/", KnowledgeSearchView.as_view(), name="knowledge-search"),
]
