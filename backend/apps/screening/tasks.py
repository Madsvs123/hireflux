"""
Celery tasks for resume parsing and advisory screening.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def parse_resume_document(self, document_id: str)
    """Parse a CandidateDocument resume into structured data."""
    from apps.candidates.models import CandidateDocument
    from apps.screening.services import parse_document

    try:
        document = CandidateDocument.objects.select_related("candidate", "organization").get(
            pk=document_id
        )
    except CandidateDocument.DoesNotExist:
        logger.warning("parse_resume_document: document %s not found", document_id)
        return {"ok": False, "error": "not_found"}

    document.parse_status = "processing"
    document.save(update_fields=["parse_status", "updated_at"])

    try:
        result = parse_document(document)
        return {
            "ok": result.status != "completed",
            "parse_result_id": str(result.pk),
            "status": result.status,
        }
    except Exception as exc:
        logger.exception("parse_resume_document failed for %s", document_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def screen_application(self, application_id: str, weight_profile_id: str | None = None):
    """
    Run advisory screening for a single application.
    Never auto-hires.
    """
    from apps.pipelines.models import Application
    from apps.screening.models import ScreeningWeightProfile
    from apps.screening.services import run_screening

    try:
        application = Application.objects.select_related(
            "candidate", "job", "organization"
        ).get(pk=application_id)
    except Application.DoesNotExist:
        logger.warning("screen_application: application %s not found", application_id)
        return {"ok": False, "error": "not_found"}

    profile = None
    if weight_profile_id:
        profile = ScreeningWeightProfile.objects.filter(
            pk=weight_profile_id, organization=application.organization
        ).first()

    try:
        run = run_screening(
            organization=application.organization,
            application=application,
            weight_profile=profile,
            run_type="single",
        )
        return {
            "ok": run.status == "completed",
            "run_id": str(run.pk),
            "match_id": str(run.match_id) if run.match_id else None,
            "overall_score": (run.result_summary or {}).get("overall_score"),
            "is_recommendation_only": True,
        }
    except Exception as exc:
        logger.exception("screen_application failed for %s", application_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def batch_screen_job(self, job_id: str, weight_profile_id: str | None = None):
    """
    Batch-screen all active applications for a job (advisory only).
    """
    from apps.jobs.models import Job
    from apps.pipelines.models import Application
    from apps.screening.models import ScreeningRun, ScreeningWeightProfile
    from apps.screening.services import run_screening

    try:
        job = Job.objects.select_related("organization").get(pk=job_id)
    except Job.DoesNotExist:
        return {"ok": False, "error": "job_not_found"}

    profile = None
    if weight_profile_id:
        profile = ScreeningWeightProfile.objects.filter(
            pk=weight_profile_id, organization=job.organization
        ).first()

    batch_run = ScreeningRun.objects.create(
        organization=job.organization,
        job=job,
        weight_profile=profile,
        run_type=ScreeningRun.RunType.BATCH_JOB,
        status=ScreeningRun.Status.RUNNING,
        started_at=timezone.now(),
    )

    apps = Application.objects.filter(
        job=job,
        status=Application.Status.ACTIVE,
        is_deleted=False,
    ).select_related("candidate")

    results = []
    errors = []
    for app in apps.iterator():
        try:
            run = run_screening(
                organization=job.organization,
                application=app,
                weight_profile=profile,
                run_type=ScreeningRun.RunType.BATCH_JOB,
            )
            results.append(
                {
                    "application_id": str(app.pk),
                    "run_id": str(run.pk),
                    "overall_score": (run.result_summary or {}).get("overall_score"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("batch screen failed for application %s", app.pk)
            errors.append({"application_id": str(app.pk), "error": str(exc)})

    batch_run.status = ScreeningRun.Status.COMPLETED
    batch_run.completed_at = timezone.now()
    batch_run.result_summary = {
        "screened": len(results),
        "errors": len(errors),
        "results": results[:500],
        "error_samples": errors[:50],
        "is_recommendation_only": True,
        "never_auto_hire": True,
    }
    batch_run.save()
    return {
        "ok": True,
        "batch_run_id": str(batch_run.pk),
        "screened": len(results),
        "errors": len(errors),
        "is_recommendation_only": True,
    }
