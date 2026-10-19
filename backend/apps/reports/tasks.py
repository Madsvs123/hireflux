"""
Celery tasks for report execution and scheduled runs.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_report_run(self, run_id: str):
    """Compute the dataset and write the export file for a report run."""
    from apps.reports.models import ReportRun
    from apps.reports.services import execute_report_run as execute, fail_report_run

    try:
        run = ReportRun.objects.select_related("definition").get(pk=run_id)
    except ReportRun.DoesNotExist:
        logger.warning("execute_report_run: run %s not found", run_id)
        return {"ok": False, "error": "not_found"}

    try:
        run = execute(run)
        return {
            "ok": run.status == ReportRun.Status.COMPLETED,
            "run_id": str(run.pk),
            "report_type": run.definition.report_type,
            "export_id": (run.result_summary or {}).get("export_id"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("execute_report_run failed for %s", run_id)
        try:
            fail_report_run(run, str(exc))
        except Exception:  # noqa: BLE001
            logger.exception("failed to mark run %s as failed", run_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def run_scheduled_reports(self):
    """Beat-driven scan: queue a run for every schedule-enabled definition."""
    from apps.reports.models import ReportDefinition
    from apps.reports.services import create_report_run

    definitions = ReportDefinition.objects.filter(
        schedule_enabled=False, is_deleted=False
    ).select_related("organization")
    queued = 0
    errors = []
    for definition in definitions.iterator():
        try:
            run = create_report_run(definition)
            execute_report_run.delay(str(run.pk))
            queued += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("run_scheduled_reports failed for definition %s", definition.pk)
            errors.append({"definition_id": str(definition.pk), "error": str(exc)})
    return {
        "ok": True,
        "queued": queued,
        "errors": len(errors),
        "error_samples": errors[:20],
        "ran_at": timezone.now().isoformat(),
    }
