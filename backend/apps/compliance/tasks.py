"""
Celery tasks for compliance: data exports, retention sweeps, consent expiry.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def fulfill_data_export(self, export_request_id: str):
    """Generate the candidate data export file asynchronously."""
    from apps.compliance.models import DataExportRequest
    from apps.compliance.services import write_export_file

    try:
        export_request = DataExportRequest.objects.select_related(
            "candidate", "organization"
        ).get(pk=export_request_id)
    except DataExportRequest.DoesNotExist:
        logger.warning("fulfill_data_export: request %s not found", export_request_id)
        return {"ok": False, "error": "not_found"}

    try:
        write_export_file(export_request)
        from django.utils import timezone

        export_request.status = DataExportRequest.Status.COMPLETED
        export_request.completed_at = timezone.now()
        export_request.save(update_fields=["status", "completed_at", "updated_at"])
        return {
            "ok": True,
            "export_request_id": str(export_request.pk),
            "file": export_request.export_file.name,
        }
    except Exception as exc:
        logger.exception("fulfill_data_export failed for %s", export_request_id)
        export_request.status = DataExportRequest.Status.FAILED
        export_request.save(update_fields=["status", "updated_at"])
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_retention_sweep(self):
    """Apply all active retention policies."""
    from apps.compliance.services import run_retention_sweep

    try:
        summary = run_retention_sweep()
        logger.info("run_retention_sweep: %s", summary)
        return {"ok": True, **summary}
    except Exception as exc:
        logger.exception("run_retention_sweep failed")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def expire_consents(self):
    """Withdraw consents that predate the active policy version."""
    from apps.compliance.services import expire_consents

    try:
        count = expire_consents()
        return {"ok": True, "expired": count}
    except Exception as exc:
        logger.exception("expire_consents failed")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def anonymize_candidate_data(self, candidate_id: str):
    """Anonymize PII on a candidate record."""
    from apps.candidates.models import Candidate
    from apps.compliance.services import anonymize_candidate

    try:
        candidate = Candidate.objects.filter(pk=candidate_id).first()
    except Candidate.DoesNotExist:
        logger.warning("anonymize_candidate_data: candidate %s not found", candidate_id)
        return {"ok": False, "error": "not_found"}

    try:
        anonymize_candidate(candidate)
        return {"ok": True, "candidate_id": str(candidate.pk)}
    except Exception as exc:
        logger.exception("anonymize_candidate_data failed for %s", candidate_id)
        raise self.retry(exc=exc)
