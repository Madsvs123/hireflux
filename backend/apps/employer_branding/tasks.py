"""
Celery tasks for employer branding: careers site cache refresh.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def regenerate_careers_cache(self):
    """Recompute and cache every enabled public careers site."""
    from apps.employer_branding.services import regenerate_careers_cache as refresh

    try:
        result = refresh()
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        logger.exception("regenerate_careers_cache failed")
        raise self.retry(exc=exc)
