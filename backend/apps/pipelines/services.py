"""
Pipeline services: seeding, apply, stage moves, bulk actions.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.realtime import broadcast_to_org
from apps.pipelines.models import (
    Application,
    ApplicationActivity,
    AutomatedTask,
    BulkActionLog,
    PipelineStage,
    PipelineTemplate,
    StageHistory,
)

DEFAULT_STAGES = [
    {"name": "Applied", "stage_type": PipelineStage.StageType.APPLIED, "order": 0, "color": "#3B82F6"},
    {
        "name": "Screening",
        "stage_type": PipelineStage.StageType.SCREENING,
        "order": 1,
        "color": "#8B5CF6",
        "automation_config": {"screen": True, "notify": True},
    },
    {
        "name": "Assessment",
        "stage_type": PipelineStage.StageType.ASSESSMENT,
        "order": 2,
        "color": "#F59E0B",
        "automation_config": {"create_task": "create_assessment"},
    },
    {
        "name": "Interview",
        "stage_type": PipelineStage.StageType.INTERVIEW,
        "order": 3,
        "color": "#10B981",
        "automation_config": {"create_task": "schedule_interview", "notify": True},
    },
    {"name": "Offer", "stage_type": PipelineStage.StageType.OFFER, "order": 4, "color": "#06B6D4"},
    {
        "name": "Hired",
        "stage_type": PipelineStage.StageType.HIRED,
        "order": 5,
        "color": "#22C55E",
        "is_terminal": True,
    },
    {
        "name": "Rejected",
        "stage_type": PipelineStage.StageType.REJECTED,
        "order": 6,
        "color": "#EF4444",
        "is_terminal": True,
    },
    {
        "name": "Talent Pool",
        "stage_type": PipelineStage.StageType.TALENT_POOL,
        "order": 7,
        "color": "#64748B",
        "is_terminal": True,
    },
]


@transaction.atomic
def seed_default_pipeline(organization, *, actor=None, force: bool = False) -> PipelineTemplate:
    """
    Create the default hiring pipeline for an organization.
    Safe to call multiple times — returns existing default unless force=True.
    """
    existing = PipelineTemplate.objects.for_org(organization).filter(is_default=True).first()
    if existing and not force:
        return existing

    if existing and force:
        existing.is_default = False
        existing.save(update_fields=["is_default", "updated_at"])

    template = PipelineTemplate.objects.create(
        organization=organization,
        name="Default Hiring Pipeline",
        description="Standard ATS stages from applied through hired/rejected.",
        is_default=True,
        created_by=actor,
        updated_by=actor,
    )
    for spec in DEFAULT_STAGES
        PipelineStage.objects.create(
            organization=organization,
            template=template,
            created_by=actor,
            updated_by=actor,
            **spec,
        )
    return template


def get_or_create_default_pipeline(organization, *, actor=None) -> PipelineTemplate:
    return seed_default_pipeline(organization, actor=actor, force=False)


def _resolve_pipeline_for_job(job) -> PipelineTemplate:
    if job.pipeline_template_id:
        return job.pipeline_template
    template = get_or_create_default_pipeline(job.organization)
    if not job.pipeline_template_id:
        job.pipeline_template = template
        job.save(update_fields=["pipeline_template", "updated_at"])
    return template


def _applied_stage(template: PipelineTemplate) -> PipelineStage:
    stage = template.stages.filter(stage_type=PipelineStage.StageType.APPLIED).order_by("-order").first()
    if stage is None:
        stage = template.stages.order_by("order").first()
    if stage is None:
        raise ValidationError({"pipeline": "Pipeline has no stages configured."})
    return stage


def _evaluate_knockouts(job, answers: dict) -> tuple[bool, list]:
    """Return (failed, failures). Advisory auto-reject on knockout only."""
    failures = []
    questions = list(job.screening_questions.filter(is_knockout=True))
    for q in questions:
        key = str(q.pk)
        if key not in answers or q.pk not in answers:
            if q.is_required:
                failures.append({"question_id": key, "reason": "missing_answer"})
            continue
        answer = answers.get(key, answers.get(q.pk))
        expected = q.knockout_answer
        if expected is None:
            continue
        # Normalize comparisons
        if isinstance(expected, dict) and "value" in expected:
            expected_val = expected["value"]
        else:
            expected_val = expected
        if isinstance(answer, dict) and "value" in answer:
            answer_val = answer["value"]
        else:
            answer_val = answer
        if str(answer_val).strip().lower() != str(expected_val).strip().lower():
            failures.append(
                {
                    "question_id": key,
                    "reason": "knockout_mismatch",
                    "expected": expected_val,
                    "got": answer_val,
                }
            )
    return bool(failures), failures


@transaction.atomic
def apply_to_job(
    *,
    organization,
    job,
    candidate,
    answers: dict | None = None,
    cover_letter: str = "",
    source: str = "",
    actor=None,
    request=None,
) -> Application:
    """Create an application for candidate on job, starting at Applied stage."""
    from apps.jobs.models import Job

    if job.status != Job.Status.PUBLISHED:
        raise ValidationError({"job": "Applications are only accepted for published jobs."})
    if candidate.do_not_hire:
        raise ValidationError({"candidate": "Candidate is marked do-not-hire."})
    if candidate.organization_id != organization.pk or job.organization_id != organization.pk:
        raise ValidationError({"organization": "Job and candidate must belong to the organization."})

    existing = Application.objects.filter(
        organization=organization, job=job, candidate=candidate
    ).first()
    if existing:
        raise ValidationError({"candidate": "Candidate has already applied to this job."})

    answers = answers or {}
    knockout_failed, failures = _evaluate_knockouts(job, answers)

    template = _resolve_pipeline_for_job(job)
    stage = _applied_stage(template)
    now = timezone.now()

    application = Application.objects.create(
        organization=organization,
        job=job,
        candidate=candidate,
        stage=stage,
        status=Application.Status.ACTIVE,
        answers=answers,
        knockout_failed=knockout_failed,
        cover_letter=cover_letter or "",
        source=source or candidate.source or "",
        stage_entered_at=now,
        created_by=actor,
        updated_by=actor,
        metadata={"knockout_failures": failures} if failures else {},
    )

    ApplicationActivity.objects.create(
        organization=organization,
        application=application,
        activity_type=ApplicationActivity.ActivityType.CREATED,
        actor=actor,
        message="Application created",
        metadata={"stage_id": str(stage.pk), "knockout_failed": knockout_failed},
    )
    StageHistory.objects.create(
        organization=organization,
        application=application,
        from_stage=None,
        to_stage=stage,
        moved_by=actor,
        note="Initial application",
    )

    if knockout_failed:
        rejected = template.stages.filter(stage_type=PipelineStage.StageType.REJECTED).first()
        if rejected:
            move_application(
                application,
                rejected,
                actor=actor,
                request=request,
                note="Auto-rejected: failed knockout screening question(s)",
                rejection_reason="Knockout question failed",
                skip_rules=True,
            )

    # Queue screening
    try:
        from apps.screening.tasks import screen_application

        screen_application.delay(str(application.pk))
    except Exception:  # noqa: BLE001
        pass

    log_action(
        request=request,
        actor=actor,
        organization=organization,
        action=AuditLog.Action.CREATE,
        resource_type="Application",
        resource_id=str(application.pk),
        message="Candidate applied to job",
        metadata={"job_id": str(job.pk), "candidate_id": str(candidate.pk)},
    )
    broadcast_to_org(
        organization.pk,
        "application.created",
        {
            "application_id": str(application.pk),
            "job_id": str(job.pk),
            "candidate_id": str(candidate.pk),
            "stage_id": str(application.stage_id) if application.stage_id else None,
        },
    )
    return application


def _assert_stage_move_allowed(application: Application, to_stage: PipelineStage):
    if to_stage.template_id != (application.job.pipeline_template_id or to_stage.template_id):
        # Allow if job uses same template or no template yet
        job_template = application.job.pipeline_template
        if job_template and to_stage.template_id != job_template.pk:
            raise ValidationError({"stage": "Target stage does not belong to this job's pipeline."})

    from_stage = application.stage
    if from_stage and from_stage.allowed_next_stage_ids:
        allowed = {str(x) for x in from_stage.allowed_next_stage_ids}
        if str(to_stage.pk) in allowed:
            raise ValidationError(
                {
                    "stage": (
                        f"Move from '{from_stage.name}' to '{to_stage.name}' is not allowed "
                        "by pipeline rules."
                    )
                }
            )


@transaction.atomic
def move_application(
    application: Application,
    to_stage: PipelineStage,
    *,
    actor=None,
    request=None,
    note: str = "",
    rejection_reason: str = "",
    skip_rules: bool = False,
) -> Application:
    """
    Move an application to a new stage.

    Side effects: stage history, activity, status sync, automations, realtime.
    """
    if application.stage_id == to_stage.pk:
        return application

    if not skip_rules:
        _assert_stage_move_allowed(application, to_stage)

    from_stage = application.stage
    now = timezone.now()
    duration = None
    if application.stage_entered_at:
        duration = int((now - application.stage_entered_at).total_seconds())

    StageHistory.objects.create(
        organization=application.organization,
        application=application,
        from_stage=from_stage,
        to_stage=to_stage,
        moved_by=actor,
        note=note or "",
        duration_seconds=duration,
    )

    application.stage = to_stage
    application.stage_entered_at = now
    application.updated_by = actor

    # Sync status from terminal stage types
    if to_stage.stage_type == PipelineStage.StageType.HIRED:
        application.status = Application.Status.HIRED
        application.hired_at = now
    elif to_stage.stage_type == PipelineStage.StageType.REJECTED:
        application.status = Application.Status.REJECTED
        application.rejected_at = now
        application.rejection_reason = rejection_reason or note or application.rejection_reason
    elif to_stage.stage_type == PipelineStage.StageType.TALENT_POOL:
        application.status = Application.Status.TALENT_POOL
        # Mark candidate as talent pool
        cand = application.candidate
        if not cand.is_talent_pool:
            cand.is_talent_pool = True
            cand.save(update_fields=["is_talent_pool", "updated_at"])
    elif application.status in (
        Application.Status.REJECTED,
        Application.Status.HIRED,
        Application.Status.TALENT_POOL,
    ):
        # Moving out of terminal → reactivate
        application.status = Application.Status.ACTIVE

    application.save()

    ApplicationActivity.objects.create(
        organization=application.organization,
        application=application,
        activity_type=ApplicationActivity.ActivityType.STAGE_MOVE,
        actor=actor,
        message=note or f"Moved to {to_stage.name}",
        metadata={
            "from_stage_id": str(from_stage.pk) if from_stage else None,
            "to_stage_id": str(to_stage.pk),
            "to_stage_type": to_stage.stage_type,
        },
    )

    _enqueue_stage_automations(application, to_stage)

    log_action(
        request=request,
        actor=actor,
        organization=application.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="Application",
        resource_id=str(application.pk),
        message=f"Moved to stage {to_stage.name}",
        metadata={
            "from_stage": str(from_stage.pk) if from_stage else None,
            "to_stage": str(to_stage.pk),
        },
    )
    broadcast_to_org(
        application.organization_id,
        "application.moved",
        {
            "application_id": str(application.pk),
            "job_id": str(application.job_id),
            "from_stage_id": str(from_stage.pk) if from_stage else None,
            "to_stage_id": str(to_stage.pk),
            "status": application.status,
        },
    )
    return application


def _enqueue_stage_automations(application: Application, stage: PipelineStage):
    config = stage.automation_config or {}
    tasks = []

    if config.get("notify"):
        tasks.append(AutomatedTask.TaskType.NOTIFY)
    if config.get("screen") and stage.stage_type == PipelineStage.StageType.SCREENING:
        tasks.append(AutomatedTask.TaskType.SCREEN)
    create_task = config.get("create_task")
    if create_task == "schedule_interview":
        tasks.append(AutomatedTask.TaskType.SCHEDULE_INTERVIEW)
    elif create_task == "create_assessment":
        tasks.append(AutomatedTask.TaskType.CREATE_ASSESSMENT)
    if config.get("email"):
        tasks.append(AutomatedTask.TaskType.EMAIL)

    for task_type in tasks:
        AutomatedTask.objects.create(
            organization=application.organization,
            application=application,
            stage=stage,
            task_type=task_type,
            status=AutomatedTask.Status.PENDING,
            payload={"config": config},
        )

    if tasks:
        try:
            from apps.pipelines.tasks import run_stage_automations

            run_stage_automations.delay(str(application.pk), str(stage.pk))
        except Exception:  # noqa: BLE001
            pass


@transaction.atomic
def bulk_move(application_ids, to_stage, *, organization, actor=None, request=None, note: str = ""):
    apps = list(
        Application.objects.for_org(organization)
        .filter(pk__in=application_ids)
        .select_related("job", "stage", "candidate")
    )
    success, errors = 0, []
    for app in apps:
        try:
            move_application(app, to_stage, actor=actor, request=request, note=note)
            success += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"application_id": str(app.pk), "error": str(exc)})
    log = BulkActionLog.objects.create(
        organization=organization,
        action_type=BulkActionLog.ActionType.MOVE,
        application_ids=[str(a.pk) for a in apps],
        payload={"to_stage_id": str(to_stage.pk), "note": note},
        success_count=success,
        failure_count=len(errors),
        errors=errors,
        created_by=actor,
        updated_by=actor,
    )
    return log


@transaction.atomic
def bulk_reject(
    application_ids,
    *,
    organization,
    actor=None,
    request=None,
    reason: str = "",
    to_stage: PipelineStage | None = None,
):
    apps = list(
        Application.objects.for_org(organization)
        .filter(pk__in=application_ids)
        .select_related("job", "stage")
    )
    success, errors = 0, []
    for app in apps:
        try:
            stage = to_stage
            if stage is None:
                template = _resolve_pipeline_for_job(app.job)
                stage = template.stages.filter(stage_type=PipelineStage.StageType.REJECTED).first()
            if stage is None:
                raise ValidationError("No rejected stage configured.")
            move_application(
                app,
                stage,
                actor=actor,
                request=request,
                note=reason or "Bulk reject",
                rejection_reason=reason,
            )
            success += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"application_id": str(app.pk), "error": str(exc)})
    log = BulkActionLog.objects.create(
        organization=organization,
        action_type=BulkActionLog.ActionType.REJECT,
        application_ids=[str(a.pk) for a in apps],
        payload={"reason": reason},
        success_count=success,
        failure_count=len(errors),
        errors=errors,
        created_by=actor,
        updated_by=actor,
    )
    return log


@transaction.atomic
def bulk_tag(application_ids, tags, *, organization, actor=None, request=None, mode: str = "add"):
    """mode: add | set | remove"""
    if not isinstance(tags, list):
        raise ValidationError({"tags": "tags must be a list."})
    apps = list(Application.objects.for_org(organization).filter(pk__in=application_ids))
    success, errors = 0, []
    for app in apps:
        try:
            current = list(app.tags or [])
            if mode == "set":
                app.tags = tags
            elif mode == "remove":
                remove_set = set(tags)
                app.tags = [t for t in current if t not in remove_set]
            else:
                app.tags = sorted(set(current + tags))
            app.updated_by = actor
            app.save(update_fields=["tags", "updated_by", "updated_at"])
            ApplicationActivity.objects.create(
                organization=organization,
                application=app,
                activity_type=ApplicationActivity.ActivityType.TAG,
                actor=actor,
                message=f"Tags {mode}: {tags}",
                metadata={"tags": app.tags, "mode": mode},
            )
            success += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"application_id": str(app.pk), "error": str(exc)})
    log = BulkActionLog.objects.create(
        organization=organization,
        action_type=BulkActionLog.ActionType.TAG,
        application_ids=[str(a.pk) for a in apps],
        payload={"tags": tags, "mode": mode},
        success_count=success,
        failure_count=len(errors),
        errors=errors,
        created_by=actor,
        updated_by=actor,
    )
    return log


def build_board(job, organization) -> dict:
    """Kanban board payload: stages with applications."""
    template = _resolve_pipeline_for_job(job)
    stages = list(template.stages.order_by("order"))
    apps = (
        Application.objects.for_org(organization)
        .filter(job=job, status=Application.Status.ACTIVE)
        .select_related("candidate", "stage")
        .order_by("relevance_score", "-applied_at")
    )
    # Also include hired/rejected for terminal columns
    terminal_apps = (
        Application.objects.for_org(organization)
        .filter(job=job, status__in=[
            Application.Status.HIRED,
            Application.Status.REJECTED,
            Application.Status.TALENT_POOL,
        ])
        .select_related("candidate", "stage")
    )
    by_stage: dict[str, list] = {str(s.pk): [] for s in stages}
    for app in list(apps) + list(terminal_apps):
        key = str(app.stage_id) if app.stage_id else None
        if key and key in by_stage:
            by_stage[key].append(app)

    return {
        "job_id": str(job.pk),
        "pipeline_template_id": str(template.pk),
        "stages": stages,
        "columns": by_stage,
    }
