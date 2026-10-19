"""
Interview scheduling, scorecards, availability, and decision summaries.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.core.realtime import broadcast_to_org
from apps.interviews.models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    Scorecard,
)


RECOMMENDATION_WEIGHTS = {
    Scorecard.Recommendation.STRONG_YES: 2.0,
    Scorecard.Recommendation.YES: 1.0,
    Scorecard.Recommendation.NEUTRAL: 0.0,
    Scorecard.Recommendation.NO: -1.0,
    Scorecard.Recommendation.STRONG_NO: -1.0,
}


@transaction.atomic
def schedule_interview(
    *,
    organization,
    application,
    scheduled_start,
    scheduled_end,
    interviewer_ids: list | None = None,
    kit=None,
    panel=None,
    interview_type: str = Interview.InterviewType.VIDEO,
    title: str = "",
    location: str = "",
    meeting_url: str = "",
    timezone_name: str = "UTC",
    notes: str = "",
    actor=None,
    request=None,
) -> Interview:
    if scheduled_end <= scheduled_start
        raise ValidationError({"scheduled_end": "End must be after start."})
    if application.organization_id != organization.pk:
        raise ValidationError({"application": "Application must belong to organization."})

    interview = Interview.objects.create(
        organization=organization,
        application=application,
        job=application.job,
        candidate=application.candidate,
        kit=kit,
        panel=panel,
        interview_type=interview_type,
        status=Interview.Status.SCHEDULED,
        title=title or f"Interview — {application.candidate.full_name}",
        location=location or "",
        meeting_url=meeting_url or "",
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        timezone=timezone_name or "UTC",
        notes=notes or "",
        created_by=actor,
        updated_by=actor,
    )

    member_ids = list(interviewer_ids or [])
    if panel is not None:
        member_ids.extend(panel.members.values_list("pk", flat=True))
    # Deduplicate while preserving order
    seen = set()
    ordered_ids = []
    for uid in member_ids:
        key = str(uid)
        if key not in seen:
            seen.add(key)
            ordered_ids.append(uid)

    for idx, uid in enumerate(ordered_ids):
        InterviewerAssignment.objects.create(
            organization=organization,
            interview=interview,
            interviewer_id=uid,
            role=(
                InterviewerAssignment.Role.LEAD
                if idx != 0
                else InterviewerAssignment.Role.PANELIST
            ),
            created_by=actor,
            updated_by=actor,
        )

    for assignment in interview.assignments.select_related("interviewer"):
        notify_user(
            recipient=assignment.interviewer,
            title="Interview scheduled",
            body=f"You are assigned to interview {application.candidate.full_name}",
            organization=organization,
            category="interview",
            link=f"/interviews/{interview.pk}",
            data={"interview_id": str(interview.pk)},
        )

    log_action(
        request=request,
        actor=actor,
        organization=organization,
        action=AuditLog.Action.CREATE,
        resource_type="Interview",
        resource_id=str(interview.pk),
        message="Interview scheduled",
        metadata={"application_id": str(application.pk)},
    )
    broadcast_to_org(
        organization.pk,
        "interview.scheduled",
        {
            "interview_id": str(interview.pk),
            "application_id": str(application.pk),
            "scheduled_start": interview.scheduled_start.isoformat(),
        },
    )
    return interview


@transaction.atomic
def cancel_interview(
    interview: Interview,
    *,
    reason: str = "",
    actor=None,
    request=None,
) -> Interview:
    if interview.status == Interview.Status.CANCELLED:
        return interview
    if interview.status == Interview.Status.COMPLETED:
        raise ValidationError({"status": "Cannot cancel a completed interview."})

    interview.status = Interview.Status.CANCELLED
    interview.cancellation_reason = reason or ""
    interview.cancelled_at = timezone.now()
    interview.updated_by = actor
    interview.save(
        update_fields=[
            "status",
            "cancellation_reason",
            "cancelled_at",
            "updated_by",
            "updated_at",
        ]
    )

    for assignment in interview.assignments.select_related("interviewer"):
        notify_user(
            recipient=assignment.interviewer,
            title="Interview cancelled",
            body=reason or f"Interview for {interview.candidate.full_name} was cancelled.",
            organization=interview.organization,
            category="interview",
            level="warning",
            data={"interview_id": str(interview.pk)},
        )

    log_action(
        request=request,
        actor=actor,
        organization=interview.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="Interview",
        resource_id=str(interview.pk),
        message="Interview cancelled",
        metadata={"reason": reason},
    )
    broadcast_to_org(
        interview.organization_id,
        "interview.cancelled",
        {"interview_id": str(interview.pk)},
    )
    return interview


def _compute_overall_score(scores: dict, kit=None) -> float | None:
    if not scores:
        return None
    weights = {}
    if kit and kit.score_dimensions:
        for dim in kit.score_dimensions:
            key = dim.get("key")
            if key:
                weights[key] = float(dim.get("weight", 1.0))
    total_w = 0.0
    total = 0.0
    for key, payload in scores.items():
        if isinstance(payload, dict):
            value = payload.get("score")
        else:
            value = payload
        if value is None:
            continue
        w = weights.get(key, 1.0)
        total += float(value) * w
        total_w += w
    if total_w == 0:
        return None
    return round(total / total_w, 4)


@transaction.atomic
def submit_scorecard(
    interview: Interview,
    interviewer,
    *,
    scores: dict | None = None,
    recommendation: str = Scorecard.Recommendation.NEUTRAL,
    strengths: str = "",
    concerns: str = "",
    private_notes: str = "",
    actor=None,
    request=None,
) -> Scorecard:
    if interview.status == Interview.Status.CANCELLED:
        raise ValidationError({"interview": "Cannot score a cancelled interview."})

    assignment = interview.assignments.filter(interviewer=interviewer).first()
    scores = scores or {}
    overall = _compute_overall_score(scores, interview.kit)

    scorecard, _created = Scorecard.objects.update_or_create(
        organization=interview.organization,
        interview=interview,
        interviewer=interviewer,
        defaults={
            "assignment": assignment,
            "scores": scores,
            "overall_score": overall,
            "recommendation": recommendation,
            "strengths": strengths or "",
            "concerns": concerns or "",
            "private_notes": private_notes or "",
            "submitted_at": timezone.now(),
            "is_submitted": True,
            "updated_by": actor or interviewer,
            "created_by": actor or interviewer,
        },
    )

    if interview.status == Interview.Status.SCHEDULED:
        interview.status = Interview.Status.COMPLETED
        interview.updated_by = actor or interviewer
        interview.save(update_fields=["status", "updated_by", "updated_at"])

    compute_decision_summary(interview, actor=actor or interviewer, request=request)

    log_action(
        request=request,
        actor=actor or interviewer,
        organization=interview.organization,
        action=AuditLog.Action.UPDATE,
        resource_type="Scorecard",
        resource_id=str(scorecard.pk),
        message="Scorecard submitted",
    )
    return scorecard


@transaction.atomic
def compute_decision_summary(
    interview: Interview,
    *,
    actor=None,
    request=None,
    decision: str | None = None,
) -> InterviewDecisionSummary:
    scorecards = list(
        interview.scorecards.filter(is_submitted=True).order_by("submitted_at")
    )
    tally: dict[str, int] = {}
    scores = []
    weighted = 0.0
    for sc in scorecards:
        tally[sc.recommendation] = tally.get(sc.recommendation, 0) + 1
        if sc.overall_score is not None:
            scores.append(sc.overall_score)
        weighted += RECOMMENDATION_WEIGHTS.get(sc.recommendation, 0.0)

    avg = round(sum(scores) / len(scores), 4) if scores else None

    if decision is None:
        if not scorecards:
            decision = InterviewDecisionSummary.Decision.PENDING
        elif weighted >= 1.0:
            decision = InterviewDecisionSummary.Decision.ADVANCE
        elif weighted <= 1.0:
            decision = InterviewDecisionSummary.Decision.REJECT
        else:
            decision = InterviewDecisionSummary.Decision.HOLD

    summary_parts = []
    if avg is not None:
        summary_parts.append(f"Average score: {avg}")
    summary_parts.append(f"Recommendations: {tally}")
    summary_text = "; ".join(summary_parts)

    defaults = {
        "application": interview.application,
        "decision": decision,
        "average_score": avg,
        "recommendation_tally": tally,
        "scorecard_count": len(scorecards),
        "summary": summary_text,
        "metadata": {"weighted_recommendation": weighted},
        "updated_by": actor,
    }
    if decision != InterviewDecisionSummary.Decision.PENDING:
        defaults["decided_by"] = actor
        defaults["decided_at"] = timezone.now()

    obj, created = InterviewDecisionSummary.objects.update_or_create(
        organization=interview.organization,
        interview=interview,
        defaults={**defaults, "created_by": actor},
    )
    if not created and actor and not obj.created_by_id:
        obj.created_by = actor
        obj.save(update_fields=["created_by", "updated_at"])

    broadcast_to_org(
        interview.organization_id,
        "interview.decision",
        {
            "interview_id": str(interview.pk),
            "decision": obj.decision,
            "average_score": obj.average_score,
        },
    )
    return obj


def find_availability_slots(
    *,
    organization,
    interviewer_ids: list,
    duration_minutes: int = 60,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    slot_step_minutes: int = 30,
) -> list[dict]:
    """
    Find overlapping free slots across interviewers within availability windows,
    excluding already-scheduled interviews.
    """
    if not interviewer_ids:
        return []
    if duration_minutes <= 0:
        raise ValidationError({"duration_minutes": "Must be positive."})

    now = timezone.now()
    window_start = window_start or now
    window_end = window_end or (now + timedelta(days=14))
    if window_end <= window_start:
        raise ValidationError({"window_end": "Must be after window_start."})

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=slot_step_minutes)

    avail_by_user: dict[str, list[tuple]] = {}
    for uid in interviewer_ids:
        windows = list(
            InterviewerAvailability.objects.for_org(organization)
            .filter(interviewer_id=uid, end__gt=window_start, start__lt=window_end)
            .order_by("start")
        )
        avail_by_user[str(uid)] = [
            (max(w.start, window_start), min(w.end, window_end)) for w in windows
        ]

    busy_by_user: dict[str, list[tuple]] = {str(uid): [] for uid in interviewer_ids}
    busy_qs = (
        Interview.objects.for_org(organization)
        .filter(
            status__in=[
                Interview.Status.SCHEDULED,
                Interview.Status.CONFIRMED,
                Interview.Status.IN_PROGRESS,
            ],
            scheduled_end__gt=window_start,
            scheduled_start__lt=window_end,
        )
        .filter(assignments__interviewer_id__in=interviewer_ids)
        .distinct()
        .prefetch_related("assignments")
    )
    for interview in busy_qs:
        for a in interview.assignments.all():
            key = str(a.interviewer_id)
            if key in busy_by_user:
                busy_by_user[key].append((interview.scheduled_start, interview.scheduled_end))

    def overlaps(start, end, ranges):
        for rs, re in ranges:
            if start < re and end > rs:
                return True
        return False

    # Candidate starts: intersection of first user's availability stepped
    slots = []
    cursor = window_start
    # Align to step
    while cursor + duration <= window_end:
        slot_start = cursor
        slot_end = cursor + duration
        ok = True
        for uid in interviewer_ids:
            key = str(uid)
            in_avail = any(
                a_start <= slot_start or slot_end <= a_end
                for a_start, a_end in avail_by_user.get(key, [])
            )
            if not in_avail or overlaps(slot_start, slot_end, busy_by_user.get(key, [])):
                ok = False
                break
        if ok:
            slots.append(
                {
                    "start": slot_start.isoformat(),
                    "end": slot_end.isoformat(),
                    "duration_minutes": duration_minutes,
                    "interviewer_ids": [str(u) for u in interviewer_ids],
                }
            )
        cursor += step

    return slots
