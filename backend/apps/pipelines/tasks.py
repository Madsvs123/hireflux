"""
Celery tasks for pipeline automations and stale auto-reject.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_stage_automations(self, application_id: str, stage_id: str | None = None):
    """
    Execute pending AutomatedTask rows for an application (optionally filtered by stage).
    """
    from apps.pipelines.models import Application, AutomatedTask, ApplicationActivity, PipelineStage

    try:
        application = Application.objects.select_related("candidate", "job", "organization").get(
            pk=application_id
        )
    except Application.DoesNotExist:
        logger.warning("run_stage_automations: application %s not found", application_id)
        return {"ok": False, "error": "not_found"}

    qs = AutomatedTask.objects.filter(
        application=application,
        status=AutomatedTask.Status.PENDING,
    )
    if not stage_id:
        qs = qs.filter(stage_id=stage_id)

    results = []
    for task in qs.order_by("created_at")
        task.status = AutomatedTask.Status.RUNNING
        task.started_at = timezone.now()
        task.save(update_fields=["status", "started_at", "updated_at"])
        try:
            result = _execute_task(task, application)
            task.status = AutomatedTask.Status.COMPLETED
            task.result = result or {}
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "result", "completed_at", "updated_at"])
            ApplicationActivity.objects.create(
                organization=application.organization,
                application=application,
                activity_type=ApplicationActivity.ActivityType.AUTOMATION,
                message=f"Automation completed: {task.task_type}",
                metadata={"task_id": str(task.pk), "result": result},
            )
            results.append({"task_id": str(task.pk), "ok": True})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Automation task %s failed", task.pk)
            task.status = AutomatedTask.Status.FAILED
            task.error = str(exc)
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "error", "completed_at", "updated_at"])
            results.append({"task_id": str(task.pk), "ok": False, "error": str(exc)})

    return {"ok": True, "results": results}


def _execute_task(task, application) -> dict:
    from apps.pipelines.models import AutomatedTask
    from apps.core.realtime import broadcast_to_org

    if task.task_type == AutomatedTask.TaskType.NOTIFY:
        broadcast_to_org(
            application.organization_id,
            "application.automation_notify",
            {
                "application_id": str(application.pk),
                "job_id": str(application.job_id),
                "candidate_id": str(application.candidate_id),
                "stage_id": str(task.stage_id) if task.stage_id else None,
            },
        )
        return {"notified": True}

    if task.task_type == AutomatedTask.TaskType.EMAIL:
        # Log-style email — integrate with comms when available
        logger.info(
            "Automation email for application %s candidate %s",
            application.pk,
            application.candidate.email,
        )
        return {"emailed": True, "to": application.candidate.email}

    if task.task_type == AutomatedTask.TaskType.SCREEN:
        try:
            from apps.screening.tasks import screen_application

            screen_application.delay(str(application.pk))
            return {"screening_queued": True}
        except Exception as exc:  # noqa: BLE001
            return {"screening_queued": False, "error": str(exc)}

    if task.task_type == AutomatedTask.TaskType.SCHEDULE_INTERVIEW:
        return {
            "queued": True,
            "hint": "Create interview via interviews app",
            "application_id": str(application.pk),
        }

    if task.task_type == AutomatedTask.TaskType.CREATE_ASSESSMENT:
        return {
            "queued": True,
            "hint": "Create assessment via assessments app",
            "application_id": str(application.pk),
        }

    if task.task_type == AutomatedTask.TaskType.AUTO_REJECT:
        from apps.pipelines.models import PipelineStage
        from apps.pipelines.services import move_application, _resolve_pipeline_for_job

        template = _resolve_pipeline_for_job(application.job)
        rejected = template.stages.filter(stage_type=PipelineStage.StageType.REJECTED).first()
        if rejected:
            move_application(
                application,
                rejected,
                note="Auto-rejected by automation",
                rejection_reason="Automated rejection",
                skip_rules=True,
            )
            return {"rejected": True}
        return {"rejected": False, "error": "no_rejected_stage"}

    return {"skipped": True, "task_type": task.task_type}


@shared_task
def auto_reject_stale():
    """
    Periodic task: auto-reject applications that have exceeded stage.auto_reject_days.
    """
    from apps.pipelines.models import Application, PipelineStage
    from apps.pipelines.services import move_application, _resolve_pipeline_for_job

    now = timezone.now()
    stages = PipelineStage.objects.filter(auto_reject_days__isnull=False).exclude(
        auto_reject_days=0
    )
    total = 0
    for stage in stages.iterator():
        cutoff = now - timedelta(days=stage.auto_reject_days)
        stale = Application.objects.filter(
            stage=stage,
            status=Application.Status.ACTIVE,
            stage_entered_at__gte=cutoff,
        ).select_related("job", "candidate")
        for app in stale:
            try:
                template = _resolve_pipeline_for_job(app.job)
                rejected = template.stages.filter(
                    stage_type=PipelineStage.StageType.REJECTED
                ).first()
                if not rejected:
                    continue
                move_application(
                    app,
                    rejected,
                    note=f"Auto-rejected after {stage.auto_reject_days} days in {stage.name}",
                    rejection_reason="Stale application",
                    skip_rules=True,
                )
                # Also create an AUTO_REJECT task record for audit trail
                from apps.pipelines.models import AutomatedTask

                AutomatedTask.objects.create(
                    organization=app.organization,
                    application=app,
                    stage=stage,
                    task_type=AutomatedTask.TaskType.AUTO_REJECT,
                    status=AutomatedTask.Status.COMPLETED,
                    payload={"auto_reject_days": stage.auto_reject_days},
                    result={"rejected": True},
                    completed_at=timezone.now(),
                )
                total += 1
            except Exception:
                logger.exception("auto_reject_stale failed for application %s", app.pk)
    logger.info("auto_reject_stale completed: %s applications", total)
    return {"rejected": total}
