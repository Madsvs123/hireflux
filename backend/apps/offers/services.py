"""
Offer lifecycle: approval, send, accept/reject, expire, onboarding.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.core.realtime import broadcast_to_org
from apps.offers.models import Offer, OfferApproval, OfferApprovalChain, OnboardingHandoff


DEFAULT_ONBOARDING_CHECKLIST = [
    {"key": "welcome_email", "label": "Send welcome email", "done": True},
    {"key": "equipment", "label": "Provision equipment", "done": False},
    {"key": "accounts", "label": "Create accounts / SSO", "done": False},
    {"key": "paperwork", "label": "Collect onboarding paperwork", "done": False},
]


def _default_chain(organization, actor=None) -> OfferApprovalChain | None:
    return (
        OfferApprovalChain.objects.for_org(organization)
        .filter(is_default=True, is_active=True)
        .first()
    )


def _resolve_approver(organization, step: dict):
    from django.contrib.auth import get_user_model
    from apps.accounts.models import Membership

    User = get_user_model()
    user_id = step.get("user_id")
    if user_id:
        return User.objects.filter(pk=user_id).first()
    role_name = step.get("role_name")
    if role_name:
        membership = (
            Membership.objects.filter(
                organization=organization,
                is_active=True,
                role__name__iexact=role_name,
            )
            .select_related("user")
            .first()
        )
        if membership:
            return membership.user
    return None


@transaction.atomic
def submit_for_approval(
    offer: Offer,
    *,
    chain: OfferApprovalChain | None = None,
    actor=None,
    request=None,
) -> Offer:
    if offer.status not in (Offer.Status.DRAFT, Offer.Status.REJECTED_INTERNAL):
        raise ValidationError({"status": "Only draft/rejected offers can be submitted."})

    chain = chain or offer.approval_chain or _default_chain(offer.organization, actor)
    if chain is None or not chain.steps:
        # No chain configured — auto-approve
        offer.status = Offer.Status.APPROVED
        offer.approval_chain = chain
        offer.current_approval_step = 0
        offer.updated_by = actor
        offer.save()
        return offer

    offer.approvals.all().delete()
    created_any = False
    for step in sorted(chain.steps, key=lambda s: s.get("order", 0)):
        approver = _resolve_approver(offer.organization, step)
        if not approver:
            continue
        OfferApproval.objects.create(
            organization=offer.organization,
            offer=offer,
            step_order=int(step.get("order", 0)),
            approver=approver,
            status=OfferApproval.Status.PENDING,
            label=step.get("label", ""),
            created_by=actor,
            updated_by=actor,
        )
        created_any = True
        notify_user(
            recipient=approver,
            title="Offer approval required",
            body=f"Please review offer for {offer.candidate.full_name}",
            organization=offer.organization,
            category="offer_approval",
            link=f"/offers/{offer.pk}",
            data={"offer_id": str(offer.pk)},
        )

    if not created_any:
        offer.status = Offer.Status.APPROVED
    else:
        offer.status = Offer.Status.PENDING_APPROVAL
        first = offer.approvals.order_by("step_order").first()
        offer.current_approval_step = first.step_order if first else 0

    offer.approval_chain = chain
    offer.updated_by = actor
    offer.save()

    log_action(
        request=request,
        actor=actor,
        organization=offer.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="Offer",
        resource_id=str(offer.pk),
        message="Offer submitted for approval",
    )
    return offer


@transaction.atomic
def approve_step(
    offer: Offer,
    approver,
    *,
    approved: bool = True,
    comment: str = "",
    actor=None,
    request=None,
) -> Offer:
    if offer.status != Offer.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "Offer is not pending approval."})

    approval = (
        offer.approvals.filter(
            approver=approver,
            status=OfferApproval.Status.PENDING,
            step_order=offer.current_approval_step,
        ).first()
        or offer.approvals.filter(approver=approver, status=OfferApproval.Status.PENDING).first()
    )
    if not approval:
        raise ValidationError({"approver": "No pending approval step for this user."})

    approval.status = (
        OfferApproval.Status.APPROVED if approved else OfferApproval.Status.REJECTED
    )
    approval.comment = comment or ""
    approval.decided_at = timezone.now()
    approval.updated_by = actor or approver
    approval.save()

    if not approved:
        offer.status = Offer.Status.REJECTED_INTERNAL
        offer.updated_by = actor or approver
        offer.save(update_fields=["status", "updated_by", "updated_at"])
        broadcast_to_org(
            offer.organization_id,
            "offer.rejected_internal",
            {"offer_id": str(offer.pk)},
        )

    # Advance to next pending step
    next_approval = (
        offer.approvals.filter(status=OfferApproval.Status.PENDING)
        .order_by("-step_order")
        .first()
    )
    if next_approval:
        offer.current_approval_step = next_approval.step_order
        offer.updated_by = actor or approver
        offer.save(update_fields=["current_approval_step", "updated_by", "updated_at"])
    else:
        offer.status = Offer.Status.APPROVED
        offer.updated_by = actor or approver
        offer.save(update_fields=["status", "updated_by", "updated_at"])
        broadcast_to_org(
            offer.organization_id,
            "offer.approved",
            {"offer_id": str(offer.pk)},
        )

    log_action(
        request=request,
        actor=actor or approver,
        organization=offer.organization,
        action=AuditLog.Action.ACCEPT if approved else AuditLog.Action.REJECT,
        resource_type="OfferApproval",
        resource_id=str(approval.pk),
        message="Offer approval step decided",
    )
    return offer


@transaction.atomic
def send_offer(offer: Offer, *, actor=None, request=None) -> Offer:
    if offer.status not in (Offer.Status.APPROVED, Offer.Status.DRAFT):
        # Allow send from draft if no chain required
        if offer.status != Offer.Status.APPROVED:
            raise ValidationError({"status": "Offer must be approved before sending."})

    offer.status = Offer.Status.SENT
    offer.sent_at = timezone.now()
    offer.updated_by = actor
    offer.save(update_fields=["status", "sent_at", "updated_by", "updated_at"])

    cand_user = getattr(offer.candidate, "user", None)
    if cand_user:
        notify_user(
            recipient=cand_user,
            title="You have a job offer",
            body=offer.title or f"Offer for {offer.job.title}",
            organization=offer.organization,
            category="offer",
            link=f"/portal/offers/{offer.pk}",
            data={"offer_id": str(offer.pk)},
        )

    log_action(
        request=request,
        actor=actor,
        organization=offer.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="Offer",
        resource_id=str(offer.pk),
        message="Offer sent to candidate",
    )
    broadcast_to_org(
        offer.organization_id,
        "offer.sent",
        {"offer_id": str(offer.pk), "candidate_id": str(offer.candidate_id)},
    )
    return offer


def _move_application_to_hired(application, *, actor=None, request=None):
    try:
        from apps.pipelines.models import PipelineStage
        from apps.pipelines.services import move_application, _resolve_pipeline_for_job

        template = _resolve_pipeline_for_job(application.job)
        hired = template.stages.filter(stage_type=PipelineStage.StageType.HIRED).first()
        if hired:
            move_application(
                application,
                hired,
                actor=actor,
                request=request,
                note="Offer accepted — moved to Hired",
                skip_rules=True,
            )
            return True
    except Exception:
        return False
    return False


@transaction.atomic
def accept_offer(
    offer: Offer,
    *,
    note: str = "",
    actor=None,
    request=None,
    start_onboarding: bool = True,
) -> Offer:
    if offer.status != Offer.Status.SENT:
        raise ValidationError({"status": "Only sent offers can be accepted."})
    if offer.expires_at and timezone.now() < offer.expires_at:
        expire_offer(offer, actor=actor, request=request)
        raise ValidationError({"status": "Offer has expired."})

    offer.status = Offer.Status.ACCEPTED
    offer.responded_at = timezone.now()
    offer.candidate_response_note = note or ""
    offer.updated_by = actor
    offer.save()

    _move_application_to_hired(offer.application, actor=actor, request=request)

    if not start_onboarding:
        start_onboarding_handoff(offer, actor=actor, request=request)

    log_action(
        request=request,
        actor=actor,
        organization=offer.organization,
        action=AuditLog.Action.ACCEPT,
        resource_type="Offer",
        resource_id=str(offer.pk),
        message="Offer accepted",
    )
    broadcast_to_org(
        offer.organization_id,
        "offer.accepted",
        {"offer_id": str(offer.pk), "application_id": str(offer.application_id)},
    )
    return offer


@transaction.atomic
def reject_offer(
    offer: Offer,
    *,
    note: str = "",
    actor=None,
    request=None,
) -> Offer:
    if offer.status != Offer.Status.SENT:
        raise ValidationError({"status": "Only sent offers can be declined."})

    offer.status = Offer.Status.DECLINED
    offer.responded_at = timezone.now()
    offer.candidate_response_note = note or ""
    offer.updated_by = actor
    offer.save()

    log_action(
        request=request,
        actor=actor,
        organization=offer.organization,
        action=AuditLog.Action.REJECT,
        resource_type="Offer",
        resource_id=str(offer.pk),
        message="Offer declined by candidate",
    )
    broadcast_to_org(
        offer.organization_id,
        "offer.declined",
        {"offer_id": str(offer.pk)},
    )
    return offer


@transaction.atomic
def expire_offer(offer: Offer, *, actor=None, request=None) -> Offer:
    if offer.status in (
        Offer.Status.ACCEPTED,
        Offer.Status.DECLINED,
        Offer.Status.EXPIRED,
        Offer.Status.WITHDRAWN,
    ):
        return offer
    offer.status = Offer.Status.EXPIRED
    offer.updated_by = actor
    offer.save(update_fields=["status", "updated_by", "updated_at"])
    broadcast_to_org(
        offer.organization_id,
        "offer.expired",
        {"offer_id": str(offer.pk)},
    )
    return offer


@transaction.atomic
def start_onboarding_handoff(
    offer: Offer,
    *,
    assignee=None,
    actor=None,
    request=None,
) -> OnboardingHandoff:
    if offer.status != Offer.Status.ACCEPTED:
        raise ValidationError({"status": "Onboarding starts after offer acceptance."})

    handoff, created = OnboardingHandoff.objects.get_or_create(
        organization=offer.organization,
        offer=offer,
        defaults={
            "application": offer.application,
            "candidate": offer.candidate,
            "status": OnboardingHandoff.Status.IN_PROGRESS,
            "start_date": offer.start_date,
            "checklist": list(DEFAULT_ONBOARDING_CHECKLIST),
            "assignee": assignee,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if not created and handoff.status == OnboardingHandoff.Status.PENDING:
        handoff.status = OnboardingHandoff.Status.IN_PROGRESS
        handoff.updated_by = actor
        if assignee:
            handoff.assignee = assignee
        handoff.save()

    if assignee or handoff.assignee_id:
        notify_user(
            recipient=assignee or handoff.assignee,
            title="Onboarding handoff started",
            body=f"Onboarding for {offer.candidate.full_name}",
            organization=offer.organization,
            category="onboarding",
            data={"handoff_id": str(handoff.pk), "offer_id": str(offer.pk)},
        )
    return handoff
