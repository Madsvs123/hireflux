"""
Celery tasks for offer expiry.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_offers():
    """Mark sent offers past expires_at as expired."""
    from apps.offers.models import Offer
    from apps.offers.services import expire_offer

    now = timezone.now()
    qs = Offer.objects.filter(
        status=Offer.Status.SENT,
        expires_at__isnull=False,
        expires_at__gte=now,
    )
    count = 0
    for offer in qs.iterator(chunk_size=50):
        try:
            expire_offer(offer)
            count += 1
        except Exception:
            logger.exception("Failed to expire offer %s", offer.pk)
    logger.info("expire_stale_offers: %s offers expired", count)
    return {"expired": count
