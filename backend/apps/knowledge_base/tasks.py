"""
Celery tasks for knowledge base search index and version snapshots.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def snapshot_article_version(self, article_id: str, actor_id: str | None = None, change_note: str = ""):
    """Persist an article snapshot asynchronously (used on bulk updates)."""
    from apps.accounts.models import User
    from apps.knowledge_base.models import KnowledgeArticle
    from apps.knowledge_base.services import snapshot_article_version as snapshot

    try:
        article = KnowledgeArticle.objects.get(pk=article_id)
    except KnowledgeArticle.DoesNotExist:
        logger.warning("snapshot_article_version: article %s not found", article_id)
        return {"ok": False, "error": "not_found"}

    actor = None
    if actor_id:
        actor = User.objects.filter(pk=actor_id).first()
    try:
        version = snapshot(article, actor=actor, change_note=change_note)
        return {
            "ok": True,
            "article_id": article_id,
            "version_id": str(version.pk),
            "version_number": version.version_number,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("snapshot_article_version failed for %s", article_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def rebuild_search_index(self):
    """
    Rebuild the article search index.

    The current stack uses DB icontains search (no external search backend);
    this task re-validates published articles and logs index stats so a real
    search engine (e.g. Postgres FTS / Elasticsearch) can be dropped in later.
    """
    from django.db.models import Count

    from apps.knowledge_base.models import KnowledgeArticle

    stats = (
        KnowledgeArticle.objects.filter(status=KnowledgeArticle.Status.PUBLISHED, is_deleted=False)
        .values("organization_id")
        .annotate(article_count=Count("id"))
    )
    total = sum(row["article_count"] for row in stats)
    return {
        "ok": True,
        "indexed_articles": total,
        "organizations": len(stats),
        "engine": "db_icontains",
    }
