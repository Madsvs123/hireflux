"""
Knowledge base services: versioning, lifecycle, votes, search.
"""
from __future__ import annotations

import difflib

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.knowledge_base.models import (
    ArticleVote,
    KnowledgeArticle,
    KnowledgeArticleVersion,
)


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


@transaction.atomic
def snapshot_article_version(
    article: KnowledgeArticle, *, actor=None, change_note: str = ""
) -> KnowledgeArticleVersion:
    """Persist the current article state as the next version number."""
    last = (
        KnowledgeArticleVersion.objects.filter(article=article, is_deleted=False)
        .order_by("-version_number")
        .first()
    )
    version = KnowledgeArticleVersion.objects.create(
        organization=article.organization,
        article=article,
        version_number=(last.version_number + 1) if last else 1,
        title=article.title,
        body_html=article.body_html,
        change_note=change_note,
        created_by=actor,
        updated_by=actor,
    )
    return version


@transaction.atomic
def publish_article(article: KnowledgeArticle, *, actor=None) -> KnowledgeArticle:
    """Publish a draft article (idempotent for already-published)."""
    if article.status == KnowledgeArticle.Status.ARCHIVED:
        raise ValidationError({"status": "An archived article cannot be published."})
    if article.status != KnowledgeArticle.Status.PUBLISHED:
        snapshot_article_version(article, actor=actor, change_note="Published")
        article.status = KnowledgeArticle.Status.PUBLISHED
        article.published_at = timezone.now()
        article.published_by = actor
        article.updated_by = actor
        article.save(
            update_fields=[
                "status",
                "published_at",
                "published_by",
                "updated_at",
                "updated_by",
            ]
        )
    return article


@transaction.atomic
def archive_article(article: KnowledgeArticle, *, actor=None) -> KnowledgeArticle:
    """Archive an article."""
    if article.status == KnowledgeArticle.Status.ARCHIVED:
        return article
    article.status = KnowledgeArticle.Status.ARCHIVED
    article.updated_by = actor
    article.save(update_fields=["status", "updated_at", "updated_by"])
    return article


@transaction.atomic
def restore_version(
    article: KnowledgeArticle,
    version: KnowledgeArticleVersion,
    *,
    actor=None,
) -> KnowledgeArticle:
    """Restore an article from a historical version (snapshots current first)."""
    if version.article_id != article.pk:
        raise ValidationError({"version": "Version does not belong to this article."})
    if article.status == KnowledgeArticle.Status.ARCHIVED:
        raise ValidationError({"status": "An archived article cannot be restored from."})
    snapshot_article_version(article, actor=actor, change_note=f"Before restoring v{version.version_number}")
    article.title = version.title
    article.body_html = version.body_html
    article.updated_by = actor
    article.save(update_fields=["title", "body_html", "updated_at", "updated_by"])
    snapshot_article_version(
        article, actor=actor, change_note=f"Restored from v{version.version_number}"
    )
    return article


def diff_versions(
    version_a: KnowledgeArticleVersion, version_b: KnowledgeArticleVersion
) -> dict:
    """Unified diff of title and body between two versions of the same article."""
    if version_a.article_id != version_b.article_id:
        raise ValidationError({"version": "Versions must belong to the same article."})
    title_diff = list(
        difflib.unified_diff(
            [version_a.title],
            [version_b.title],
            fromfile=f"v{version_a.version_number} title",
            tofile=f"v{version_b.version_number} title",
        )
    )
    body_diff = list(
        difflib.unified_diff(
            (version_a.body_html or "").splitlines(),
            (version_b.body_html or "").splitlines(),
            fromfile=f"v{version_a.version_number}",
            tofile=f"v{version_b.version_number}",
        )
    )
    return {
        "from_version": version_a.version_number,
        "to_version": version_b.version_number,
        "title_diff": title_diff,
        "body_diff": body_diff,
    }


# ---------------------------------------------------------------------------
# Views & votes
# ---------------------------------------------------------------------------


def increment_view(article: KnowledgeArticle) -> KnowledgeArticle
    """Increment the view counter (atomic)."""
    KnowledgeArticle.objects.filter(pk=article.pk).update(
        view_count=F("view_count") + 1
    )
    article.refresh_from_db(fields=["view_count"])
    return article


@transaction.atomic
def toggle_vote(
    article: KnowledgeArticle, user, helpful: bool
) -> tuple[ArticleVote, bool]:
    """Create or flip a user's vote on an article. Returns (vote, created)."""
    vote, created = ArticleVote.objects.get_or_create(
        organization=article.organization,
        article=article,
        user=user,
        defaults={"helpful": helpful, "created_by": user, "updated_by": user},
    )
    if not created and vote.helpful == helpful:
        vote.helpful = helpful
        vote.updated_by = user
        vote.save(update_fields=["helpful", "updated_at", "updated_by"])
        created = True
    return vote, created


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search_articles(
    organization,
    query: str,
    *,
    category_id=None,
    include_drafts: bool = False,
) -> list[KnowledgeArticle]:
    """Search across title, summary, and body of articles."""
    qs = KnowledgeArticle.objects.for_org(organization).filter(is_deleted=False)
    if include_drafts:
        qs = qs.filter(status=KnowledgeArticle.Status.PUBLISHED)
    if category_id:
        qs = qs.filter(category_id=category_id)

    query = (query or "").strip()
    if not query:
        return list(qs.order_by("-view_count", "-created_at")[:100])

    terms = [t for t in query.split() if t]
    q_filter = Q()
    for term in terms:
        q_filter &= Q(title__icontains=term)
        q_filter &= Q(summary__icontains=term)
        q_filter &= Q(body_html__icontains=term)
    return list(qs.filter(q_filter).order_by("-view_count", "-created_at")[:100])
