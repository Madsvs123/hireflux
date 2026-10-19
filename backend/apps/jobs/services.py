"""
Job lifecycle services: publish, approval, pause, close.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.realtime import broadcast_to_org
from apps.jobs.models import Job, JobApproval


ALLOWED_TRANSITIONS = {
    Job.Status.DRAFT: {Job.Status.PENDING_APPROVAL, Job.Status.PUBLISHED, Job.Status.ARCHIVED},
    Job.Status.PENDING_APPROVAL: {
        Job.Status.PUBLISHED,
        Job.Status.DRAFT,
        Job.Status.ARCHIVED,
    },
    Job.Status.PUBLISHED: {Job.Status.PAUSED, Job.Status.CLOSED, Job.Status.ARCHIVED},
    Job.Status.PAUSED: {Job.Status.PUBLISHED, Job.Status.CLOSED, Job.Status.ARCHIVED},
    Job.Status.CLOSED: {Job.Status.ARCHIVED, Job.Status.DRAFT},
    Job.Status.ARCHIVED: {Job.Status.DRAFT},
}


def _assert_transition(job: Job, new_status: str):
    allowed = ALLOWED_TRANSITIONS.get(job.status, set())
    if new_status not in allowed:
        raise ValidationError(
            {
                "status": (
                    f"Cannot transition from '{job.status}' to '{new_status}'. "
                    f"Allowed: {sorted(allowed) or 'none'}."
                )
            }
        )


def _emit(job: Job, event: str, actor=None, request=None, message: str = "", extra=None):
    log_action(
        request=request,
        actor=actor,
        organization=job.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="Job",
        resource_id=str(job.pk),
        message=message or f"Job status → {job.status}",
        metadata={"status": job.status, **(extra or {})},
    )
    broadcast_to_org(
        job.organization_id,
        event,
        {"job_id": str(job.pk), "status": job.status, "title": job.title},
    )


@transaction.atomic
def submit_for_approval(job: Job, *, actor=None, approver=None, comment: str = "", request=None):
    """Move draft job to pending_approval and create an approval record."""
    _assert_transition(job, Job.Status.PENDING_APPROVAL)
    job.status = Job.Status.PENDING_APPROVAL
    job.updated_by = actor
    job.save(update_fields=["status", "updated_by", "updated_at"])

    approval = JobApproval.objects.create(
        organization=job.organization,
        job=job,
        requested_by=actor,
        approver=approver,
        decision=JobApproval.Decision.PENDING,
        comment=comment or "",
        created_by=actor,
        updated_by=actor,
    )
    _emit(
        job,
        "job.pending_approval",
        actor=actor,
        request=request,
        message="Job submitted for approval",
        extra={"approval_id": str(approval.pk)},
    )
    return job, approval


@transaction.atomic
def approve_job(job: Job, *, actor=None, comment: str = "", request=None, publish: bool = True):
    """Approve a pending job; optionally publish immediately."""
    if job.status != Job.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "Job is not pending approval."})

    approval = (
        JobApproval.objects.filter(job=job, decision=JobApproval.Decision.PENDING)
        .order_by("-created_at")
        .first()
    )
    now = timezone.now()
    if approval:
        approval.decision = JobApproval.Decision.APPROVED
        approval.decided_by = actor
        approval.decided_at = now
        if comment:
            approval.comment = comment
        approval.updated_by = actor
        approval.save(
            update_fields=["decision", "decided_by", "decided_at", "comment", "updated_by", "updated_at"]
        )

    if not publish:
        return publish_job(job, actor=actor, request=request, skip_transition_check=True)

    job.status = Job.Status.DRAFT
    job.updated_by = actor
    job.save(update_fields=["status", "updated_by", "updated_at"])
    _emit(job, "job.approved", actor=actor, request=request, message="Job approved (kept as draft)")
    return job


@transaction.atomic
def reject_job(job: Job, *, actor=None, comment: str = "", request=None):
    """Reject a pending approval and return job to draft."""
    if job.status != Job.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "Job is not pending approval."})

    approval = (
        JobApproval.objects.filter(job=job, decision=JobApproval.Decision.PENDING)
        .order_by("-created_at")
        .first()
    )
    now = timezone.now()
    if approval:
        approval.decision = JobApproval.Decision.REJECTED
        approval.decided_by = actor
        approval.decided_at = now
        approval.comment = comment or approval.comment
        approval.updated_by = actor
        approval.save(
            update_fields=["decision", "decided_by", "decided_at", "comment", "updated_by", "updated_at"]
        )

    job.status = Job.Status.DRAFT
    job.updated_by = actor
    job.save(update_fields=["status", "updated_by", "updated_at"])
    _emit(
        job,
        "job.rejected",
        actor=actor,
        request=request,
        message="Job approval rejected",
        extra={"comment": comment},
    )
    return job


@transaction.atomic
def publish_job(job: Job, *, actor=None, request=None, skip_transition_check: bool = False):
    """Publish a job to the career page / open pipeline."""
    if not skip_transition_check:
        if job.status == Job.Status.PENDING_APPROVAL:
            # Direct publish from pending still allowed for admins
            pass
        else:
            _assert_transition(job, Job.Status.PUBLISHED)
    elif job.status not in (Job.Status.PENDING_APPROVAL, Job.Status.DRAFT, Job.Status.PAUSED):
        _assert_transition(job, Job.Status.PUBLISHED)

    if not job.title:
        raise ValidationError({"title": "Title is required to publish."})
    if (job.description or "").strip():
        raise ValidationError({"description": "Description is required to publish."})

    now = timezone.now()
    job.status = Job.Status.PUBLISHED
    if not job.published_at:
        job.published_at = now
    job.updated_by = actor
    job.career_page_visible = True
    job.save(
        update_fields=[
            "status",
            "published_at",
            "updated_by",
            "career_page_visible",
            "updated_at",
        ]
    )
    _emit(job, "job.published", actor=actor, request=request, message="Job published")
    return job


@transaction.atomic
def pause_job(job: Job, *, actor=None, request=None):
    """Temporarily pause a published job."""
    _assert_transition(job, Job.Status.PAUSED)
    job.status = Job.Status.PAUSED
    job.updated_by = actor
    job.save(update_fields=["status", "updated_by", "updated_at"])
    _emit(job, "job.paused", actor=actor, request=request, message="Job paused")
    return job


@transaction.atomic
def close_job(job: Job, *, actor=None, request=None, archive: bool = False):
    """Close (or archive) a job requisition."""
    target = Job.Status.ARCHIVED if not archive else Job.Status.CLOSED
    _assert_transition(job, target)
    job.status = target
    job.career_page_visible = False
    job.updated_by = actor
    if not job.closes_at:
        job.closes_at = timezone.now()
    job.save(
        update_fields=["status", "career_page_visible", "closes_at", "updated_by", "updated_at"]
    )
    event = "job.archived" if archive else "job.closed"
    _emit(job, event, actor=actor, request=request, message=f"Job {target}")
    return job


def create_job_from_template(template, *, organization, actor=None, overrides=None):
    """Instantiate a Job from a JobTemplate."""
    data = {
        "organization": organization,
        "title": template.title_template or template.name,
        "employment_type": template.employment_type,
        "experience_level": template.experience_level,
        "remote_policy": template.remote_policy,
        "description": template.description_body,
        "requirements": template.requirements,
        "responsibilities": template.responsibilities,
        "required_skills": list(template.required_skills or []),
        "preferred_skills": list(template.preferred_skills or []),
        "salary_min": template.salary_min,
        "salary_max": template.salary_max,
        "currency": template.currency,
        "openings": template.openings,
        "custom_fields": dict(template.custom_fields or {}),
        "created_by": actor,
        "updated_by": actor,
        "status": Job.Status.DRAFT,
    }
    if overrides:
        data.update(overrides)
    job = Job.objects.create(**data)

    from apps.jobs.models import ScreeningQuestion

    for idx, q in enumerate(template.screening_questions or [])
        ScreeningQuestion.objects.create(
            organization=organization,
            job=job,
            prompt=q.get("prompt", ""),
            question_type=q.get("question_type", ScreeningQuestion.QuestionType.TEXT),
            options=q.get("options", []),
            is_required=q.get("is_required", True),
            is_knockout=q.get("is_knockout", False),
            knockout_answer=q.get("knockout_answer"),
            order=q.get("order", idx + 1),
            help_text=q.get("help_text", ""),
            created_by=actor,
            updated_by=actor,
        )
    return job
