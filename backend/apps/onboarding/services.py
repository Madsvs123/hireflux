"""
Onboarding business logic: template duplication, plan instantiation, task workflow.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.core.realtime import broadcast_to_org
from apps.onboarding.models import (
    OnboardingDocument,
    OnboardingPlan,
    OnboardingPlanTask,
    OnboardingTaskDefinition,
    OnboardingTemplate,
)

REMINDER_WINDOW_DAYS = 2


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
@transaction.atomic
def duplicate_template(template: OnboardingTemplate, *, actor=None) -> OnboardingTemplate:
    """Copy a template along with all of its task definitions."""
    copy = OnboardingTemplate.objects.create(
        organization=template.organization,
        name=f"{template.name} (Copy)",
        description=template.description,
        is_active=template.is_active,
        config=template.config,
        created_by=actor,
        updated_by=actor,
    )
    for definition in template.task_definitions.all():
        OnboardingTaskDefinition.objects.create(
            organization=template.organization,
            template=copy,
            title=definition.title,
            description=definition.description,
            owner_role=definition.owner_role,
            due_offset_days=definition.due_offset_days,
            required=definition.required,
            order=definition.order,
            created_by=actor,
            updated_by=actor,
        )
    return copy


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------
@transaction.atomic
def create_plan(
    organization,
    *,
    candidate,
    offer=None,
    template=None,
    start_date=None,
    actor=None,
) -> OnboardingPlan:
    """Create a draft onboarding plan for a hired candidate."""
    return OnboardingPlan.objects.create(
        organization=organization,
        candidate=candidate,
        offer=offer,
        template=template,
        status=OnboardingPlan.Status.DRAFT,
        start_date=start_date,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def start_plan(plan: OnboardingPlan, *, template=None, actor=None) -> OnboardingPlan:
    """Activate a plan and instantiate tasks from its template."""
    if plan.status not in (
        OnboardingPlan.Status.DRAFT,
        OnboardingPlan.Status.CANCELLED,
    ):
        raise ValidationError({"status": "Only draft or cancelled plans can be started."})

    if template is not None and plan.template_id is None:
        plan.template = template

    plan.status = OnboardingPlan.Status.ACTIVE
    plan.updated_by = actor
    plan.save()

    if plan.template_id and plan.tasks.exists():
        _instantiate_template_tasks(plan, plan.template, actor=actor)

    log_action(
        actor=actor,
        organization=plan.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="OnboardingPlan",
        resource_id=str(plan.pk),
        message="Onboarding plan started",
        metadata={"status": plan.status},
    )
    broadcast_to_org(
        plan.organization_id,
        "onboarding.plan_started",
        {"plan_id": str(plan.pk), "candidate_id": str(plan.candidate_id)},
    )
    return plan


def _instantiate_template_tasks(plan: OnboardingPlan, template: OnboardingTemplate, *, actor=None):
    """Create OnboardingPlanTask rows from template task definitions."""
    for definition in template.task_definitions.all():
        due_date = None
        if plan.start_date and definition.due_offset_days:
            due_date = plan.start_date + timedelta(days=definition.due_offset_days - 1)
        OnboardingPlanTask.objects.create(
            organization=plan.organization,
            plan=plan,
            definition=definition,
            title=definition.title,
            status=OnboardingPlanTask.Status.PENDING,
            due_date=due_date,
            created_by=actor,
            updated_by=actor,
        )


def plan_progress(plan: OnboardingPlan) -> dict:
    """Aggregate task/document status counts for a plan."""
    task_counts = dict(
        _status_counts(plan.tasks, OnboardingPlanTask.Status.values)
    )
    doc_counts = dict(
        _status_counts(plan.documents, OnboardingDocument.Status.values)
    )

    total_tasks = sum(task_counts.values())
    completed_tasks = task_counts.get(OnboardingPlanTask.Status.COMPLETED, 0)
    return {
        "status": plan.status,
        "tasks": task_counts,
        "documents": doc_counts,
        "task_completion_pct": round((completed_tasks / total_tasks) * 100, 1),
    }


def _status_counts(qs, valid_values):
    counts = dict(qs.values_list("status").annotate_count())
    return [(value, counts.get(value, 0)) for value in valid_values]


@transaction.atomic
def cancel_plan(plan: OnboardingPlan, *, actor=None) -> OnboardingPlan:
    if plan.status not in (
        OnboardingPlan.Status.DRAFT,
        OnboardingPlan.Status.ACTIVE,
    ):
        raise ValidationError({"status": "Only draft or active plans can be cancelled."})
    plan.status = OnboardingPlan.Status.CANCELLED
    plan.updated_by = actor
    plan.save(update_fields=["status", "updated_by", "updated_at"])
    log_action(
        actor=actor,
        organization=plan.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="OnboardingPlan",
        resource_id=str(plan.pk),
        message="Onboarding plan cancelled",
    )
    return plan


@transaction.atomic
def create_plan_from_offer(offer, *, actor=None) -> OnboardingPlan:
    """Auto-create an onboarding plan when an offer is accepted."""
    from apps.offers.models import Offer

    if offer.status != Offer.Status.ACCEPTED:
        raise ValidationError({"status": "Plan creation requires an accepted offer."})

    plan, created = OnboardingPlan.objects.get_or_create(
        organization=offer.organization,
        offer=offer,
        defaults={
            "candidate": offer.candidate,
            "status": OnboardingPlan.Status.DRAFT,
            "start_date": offer.start_date,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if not created:
        return plan

    template = (
        OnboardingTemplate.objects.for_org(offer.organization)
        .filter(is_active=True)
        .first()
    )
    if template:
        plan.template = template
        plan.save(update_fields=["template", "updated_at"])
        _instantiate_template_tasks(plan, template, actor=actor)
        plan.status = OnboardingPlan.Status.ACTIVE
        plan.updated_by = actor
        plan.save(update_fields=["status", "updated_by", "updated_at"])
        log_action(
            actor=actor,
            organization=offer.organization,
            action=AuditLog.Action.CREATE,
            resource_type="OnboardingPlan",
            resource_id=str(plan.pk),
            message="Onboarding plan auto-created from accepted offer",
            metadata={"offer_id": str(offer.pk)},
        )
    return plan


# ---------------------------------------------------------------------------
# Plan tasks
# ---------------------------------------------------------------------------
@transaction.atomic
def create_task(
    plan: OnboardingPlan,
    *,
    definition=None,
    title: str = "",
    due_date=None,
    actor=None,
) -> OnboardingPlanTask:
    """Add an ad-hoc task to a plan."""
    task = OnboardingPlanTask.objects.create(
        organization=plan.organization,
        plan=plan,
        definition=definition,
        title=title or (definition.title if definition else "Untitled task"),
        status=OnboardingPlanTask.Status.PENDING,
        due_date=due_date,
        created_by=actor,
        updated_by=actor,
    )
    return task


@transaction.atomic
def complete_task(task: OnboardingPlanTask, *, actor=None) -> OnboardingPlanTask:
    if task.status == OnboardingPlanTask.Status.COMPLETED:
        raise ValidationError({"status": "Task is already completed."})
    task.status = OnboardingPlanTask.Status.COMPLETED
    task.completed_at = timezone.now()
    task.completed_by = actor
    task.updated_by = actor
    task.save()

    plan = task.plan
    if plan.status == OnboardingPlan.Status.ACTIVE and plan.tasks.filter(
        status=OnboardingPlanTask.Status.COMPLETED
    ).exists():
        plan.status = OnboardingPlan.Status.COMPLETED
        plan.updated_by = actor
        plan.save(update_fields=["status", "updated_by", "updated_at"])
        broadcast_to_org(
            plan.organization_id,
            "onboarding.plan_completed",
            {"plan_id": str(plan.pk), "candidate_id": str(plan.candidate_id)},
        )
    return task


@transaction.atomic
def reopen_task(task: OnboardingPlanTask, *, actor=None) -> OnboardingPlanTask:
    if task.status != OnboardingPlanTask.Status.COMPLETED:
        raise ValidationError({"status": "Only completed tasks can be reopened."})
    task.status = OnboardingPlanTask.Status.PENDING
    task.completed_at = None
    task.completed_by = None
    task.updated_by = actor
    task.save()
    return task


@transaction.atomic
def block_task(task: OnboardingPlanTask, *, note: str = "", actor=None) -> OnboardingPlanTask:
    if task.status === OnboardingPlanTask.Status.COMPLETED:
        raise ValidationError({"status": "Completed tasks cannot be blocked."})
    task.status = OnboardingPlanTask.Status.BLOCKED
    task.notes = note or task.notes
    task.updated_by = actor
    task.save()
    return task


# ---------------------------------------------------------------------------
# Onboarding documents
# ---------------------------------------------------------------------------
@transaction.atomic
def upload_document(plan: OnboardingPlan, *, name: str, file=None, actor=None) -> OnboardingDocument:
    """Attach a document to a plan (missing if no file provided)."""
    return OnboardingDocument.objects.create(
        organization=plan.organization,
        plan=plan,
        name=name,
        file=file,
        status=(
            OnboardingDocument.Status.UPLOADED
            if file
            else OnboardingDocument.Status.MISSING
        ),
        uploaded_by=actor if file else None,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def approve_document(document: OnboardingDocument, *, actor=None) -> OnboardingDocument:
    if document.status != OnboardingDocument.Status.UPLOADED:
        raise ValidationError({"status": "Only uploaded documents can be approved."})
    document.status = OnboardingDocument.Status.APPROVED
    document.approved_by = actor
    document.updated_by = actor
    document.save()
    return document


@transaction.atomic
def reject_document(document: OnboardingDocument, *, actor=None) -> OnboardingDocument:
    if document.status != OnboardingDocument.Status.UPLOADED:
        raise ValidationError({"status": "Only uploaded documents can be rejected."})
    document.status = OnboardingDocument.Status.REJECTED
    document.updated_by = actor
    document.save()
    return document


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------
def send_plan_reminders(plan: OnboardingPlan, *, actor=None) -> int:
    """Notify the responsible user about due / overdue plan tasks."""
    now = timezone.now().date()
    window_end = now + timedelta(days=REMINDER_WINDOW_DAYS)
    due_tasks = plan.tasks.filter(
        status__in=[
            OnboardingPlanTask.Status.PENDING,
            OnboardingPlanTask.Status.IN_PROGRESS,
        ],
        due_date__isnull=False,
        due_date__lte=now,
    )
    recipient = _default_recipient(plan)
    if recipient is None:
        return 0
    count = 0
    for task in due_tasks:
        notify_user(
            recipient=recipient,
            title="Onboarding task reminder",
            body=f"{task.title} for {plan.candidate.full_name} is due on {task.due_date}",
            organization=plan.organization,
            category="onboarding_reminder",
            link=f"/onboarding/plans/{plan.pk}",
            data={"plan_id": str(plan.pk), "task_id": str(task.pk), "due_date": str(task.due_date)},
        )
        count += 1
    return count


def send_all_plan_reminders() -> int:
    """Remind across all active plans (Celery entry point)."""
    total = 0
    for plan in OnboardingPlan.objects.filter(status=OnboardingPlan.Status.ACTIVE):
        try:
            total += send_plan_reminders(plan)
        except Exception:  # noqa: BLE001
            continue
    return total


def _default_recipient(plan: OnboardingPlan):
    if plan.created_by_id:
        return plan.created_by
    from apps.accounts.models import Membership

    membership = (
        Membership.objects.filter(organization=plan.organization, is_active=True)
        .select_related("user")
        .first()
    )
    return membership.user if membership else None
