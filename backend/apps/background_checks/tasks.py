"""
Celery tasks for background checks: provider submission, polling, callbacks.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def submit_check_to_provider(self, request_id: str):
    """Submit a background check to the provider and schedule status polling."""
    from apps.background_checks.models import BackgroundCheckRequest
    from apps.background_checks.services import submit_to_provider

    try:
        check = BackgroundCheckRequest.objects.select_related(
            "candidate", "package", "provider", "organization"
        ).get(pk=request_id)
    except BackgroundCheckRequest.DoesNotExist:
        logger.warning("submit_check_to_provider: request %s not found", request_id)
        return {"ok": False, "error": "not_found"}

    try:
        check = submit_to_provider(check)
    except Exception as exc:
        logger.exception("submit_check_to_provider failed for %s", request_id)
        raise self.retry(exc=exc)

    # Schedule status polling once the request is in progress.
    if check.status == BackgroundCheckRequest.Status.IN_PROGRESS:
        poll_provider_status.apply_async(args=[request_id], countdown=600)
    return {
        "ok": True,
        "request_id": str(check.pk),
        "status": check.status,
        "provider_ref": check.provider_ref,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def poll_provider_status(self, request_id: str):
    """Poll the provider for completion and record the report."""
    from apps.background_checks.models import BackgroundCheckRequest
    from apps.background_checks.services import simulate_provider_report

    try:
        check = BackgroundCheckRequest.objects.select_related(
            "candidate", "package", "provider", "organization"
        ).get(pk=request_id)
    except BackgroundCheckRequest.DoesNotExist:
        logger.warning("poll_provider_status: request %s not found", request_id)
        return {"ok": False, "error": "not_found"}

    if check.status != BackgroundCheckRequest.Status.IN_PROGRESS:
        return {"ok": True, "request_id": str(check.pk), "status": check.status}

    try:
        report = simulate_provider_report(check)
        return {
            "ok": True,
            "request_id": str(check.pk),
            "report_id": str(report.pk),
            "status": check.status,
        }
    except Exception as exc:
        logger.exception("poll_provider_status failed for %s", request_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_provider_callback(self, payload: dict):
    """Process a provider callback asynchronously (webhook delegates to service)."""
    from apps.background_checks.services import process_provider_callback as service

    try:
        return service(
            provider_key=str(payload.get("provider_key") or ""),
            payload=payload.get("payload") or {},
        )
    except Exception as exc:
        logger.exception("process_provider_callback failed")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def notify_check_completed(self, request_id: str):
    """Notify the initiator that a background check completed."""
    from apps.background_checks.models import BackgroundCheckRequest
    from apps.background_checks.services import notify_check_completed as service

    try:
        check = BackgroundCheckRequest.objects.select_related(
            "initiated_by", "candidate", "organization"
        ).get(pk=request_id)
    except BackgroundCheckRequest.DoesNotExist:
        logger.warning("notify_check_completed: request %s not found", request_id)
        return {"ok": False, "error": "not_found"}

    try:
        service(check)
        return {"ok": True, "request_id": str(check.pk)}
    except Exception as exc:
        logger.exception("notify_check_completed failed for %s", request_id)
        raise self.retry(exc=exc)
