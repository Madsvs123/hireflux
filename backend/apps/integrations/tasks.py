"""
Celery tasks for webhook dispatch, connection health checks, and inbound
provider webhook processing.
"""
import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def dispatch_webhook(self, delivery_id: str):
    """Deliver a webhook with exponential backoff and HMAC signature."""
    from apps.integrations.models import WebhookDelivery
    from apps.integrations.services import (
        WebhookDeliveryError,
        perform_webhook_delivery,
    )

    try:
        delivery = WebhookDelivery.objects.select_related("endpoint", "organization").get(
            pk=delivery_id
        )
    except WebhookDelivery.DoesNotExist:
        logger.warning("dispatch_webhook: delivery %s not found", delivery_id)
        return {"ok": False, "error": "not_found"}

    if delivery.status == WebhookDelivery.Status.SUCCESS:
        return {"ok": True, "delivery_id": delivery_id, "already_delivered": True}

    try:
        ok = perform_webhook_delivery(delivery)
        return {
            "ok": ok,
            "delivery_id": delivery_id,
            "status": delivery.status,
            "attempts": delivery.attempts,
        }
    except WebhookDeliveryError as exc:
        logger.warning(
            "dispatch_webhook attempt %s failed for %s: %s",
            delivery.attempts,
            delivery_id,
            exc,
        )
        countdown = min(3600, 60 * (2 ** self.request.retries))
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            delivery.status = WebhookDelivery.Status.FAILED
            delivery.save(update_fields=["status", "updated_at"])
            logger.error(
                "dispatch_webhook gave up on %s after %s attempts",
                delivery_id,
                delivery.attempts,
            )
            return {"ok": False, "delivery_id": delivery_id, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("dispatch_webhook failed for %s", delivery_id)
        raise self.retry(exc=exc)


@shared_task
def check_connection_health():
    """Periodic health check over connected provider connections."""
    from apps.integrations.models import IntegrationConnection
    from apps.integrations.services import test_connection

    checked = 0
    errors = 0
    qs = IntegrationConnection.objects.filter(
        status=IntegrationConnection.Status.CONNECTED
    ).select_related("provider")
    for connection in qs.iterator(chunk_size=50):
        ok, message = test_connection(connection)
        checked += 1
        if not ok:
            errors += 1
        connection.status = (
            IntegrationConnection.Status.CONNECTED
            if ok
            else IntegrationConnection.Status.ERROR
        )
        connection.last_error = "" if ok else message[:1000]
        connection.save(update_fields=["status", "last_error", "updated_at"])
    logger.info("check_connection_health: %s checked, %s errors", checked, errors)
    return {"checked": checked, "errors": errors}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_provider_webhook(self, provider_key: str, payload: dict, headers: dict, request_url: str = ""):
    """Entrypoint for inbound provider callbacks (idempotent)."""
    from apps.integrations.services import process_inbound_webhook

    try:
        delivery = process_inbound_webhook(
            provider_key=provider_key,
            payload=payload or {},
            headers=headers or {},
            request_url=request_url or "",
        )
        return {
            "ok": delivery is not None,
            "delivery_id": str(delivery.pk) if delivery else None,
            "deduplicated": delivery is None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("process_provider_webhook failed for provider %s", provider_key)
        raise self.retry(exc=exc)
