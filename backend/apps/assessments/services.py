"""
Assessment assignment, scoring, and mention notification services.
"""
from __future__ import annotations

import secrets
import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.assessments.models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    HiringComment,
)
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.core.realtime import broadcast_to_org

User = get_user_model()
MENTION_RE = re.compile(r"@\[([^\]]+)\]\(([0-9a-fA-F-]{36})\)|@([^\s@]+)")


@transaction.atomic
def assign_assessment(
    *,
    organization,
    template: AssessmentTemplate,
    application,
    due_at=None,
    actor=None,
    request=None,
) -> AssessmentAssignment:
    if template.organization_id != organization.pk:
        raise ValidationError({"template": "Template must belong to organization."})
    if application.organization_id != organization.pk:
        raise ValidationError({"application": "Application must belong to organization."})
    if not template.questions.exists():
        raise ValidationError({"template": "Template has no questions."})

    assignment = AssessmentAssignment.objects.create(
        organization=organization,
        template=template,
        application=application,
        candidate=application.candidate,
        job=application.job,
        status=AssessmentAssignment.Status.PENDING,
        due_at=due_at,
        access_token=secrets.token_urlsafe(32),
        created_by=actor,
        updated_by=actor,
    )

    # Notify candidate user if linked
    cand_user = getattr(application.candidate, "user", None)
    if cand_user:
        notify_user(
            recipient=cand_user,
            title="Assessment assigned",
            body=f"Please complete: {template.name}",
            organization=organization,
            category="assessment",
            link=f"/portal/assessments/{assignment.pk}",
            data={"assignment_id": str(assignment.pk)},
        )

    log_action(
        request=request,
        actor=actor,
        organization=organization,
        action=AuditLog.Action.CREATE,
        resource_type="AssessmentAssignment",
        resource_id=str(assignment.pk),
        message="Assessment assigned",
    )
    broadcast_to_org(
        organization.pk,
        "assessment.assigned",
        {
            "assignment_id": str(assignment.pk),
            "application_id": str(application.pk),
            "template_id": str(template.pk),
        },
    )
    return assignment


def _answers_match(expected, given, question_type: str) -> bool:
    if expected is None:
        return False
    if isinstance(expected, dict) and "value" in expected:
        expected = expected["value"]
    if isinstance(given, dict) and "value" in given:
        given = given["value"]

    if question_type == AssessmentQuestion.QuestionType.MULTI_SELECT:
        exp = sorted(str(x) for x in (expected if isinstance(expected, list) else [expected]))
        got = sorted(str(x) for x in (given if isinstance(given, list) else [given]))
        return exp == got

    if question_type == AssessmentQuestion.QuestionType.TRUE_FALSE:
        def _boolish(v):
            return str(v).strip().lower() in ("true", "1", "yes")

        return _boolish(given) == _boolish(expected)

    return str(given).strip().lower() == str(expected).strip().lower()


@transaction.atomic
def score_assignment(
    assignment: AssessmentAssignment,
    *,
    actor=None,
    request=None,
) -> AssessmentAssignment:
    """Score objective/knockout questions. Subjective items left unscored (null)."""
    if assignment.status not in (
        AssessmentAssignment.Status.SUBMITTED,
        AssessmentAssignment.Status.SCORED,
        AssessmentAssignment.Status.IN_PROGRESS,
    ):
        # Allow scoring after submit primarily
        if assignment.status == AssessmentAssignment.Status.CANCELLED:
            raise ValidationError({"status": "Cannot score a cancelled assignment."})

    questions = list(assignment.template.questions.all())
    answers = {
        str(a.question_id): a
        for a in assignment.answers.select_related("question")
    }
    total_points = 0.0
    awarded = 0.0
    knockout_failed = False
    details = {"questions": []}

    for q in questions:
        total_points += float(q.points)
        ans = answers.get(str(q.pk))
        objective = q.question_type in (
            AssessmentQuestion.QuestionType.MULTIPLE_CHOICE,
            AssessmentQuestion.QuestionType.MULTI_SELECT,
            AssessmentQuestion.QuestionType.TRUE_FALSE,
        ) and q.correct_answer is not None

        if ans is None:
            entry = {"question_id": str(q.pk), "missing": True, "points_awarded": 0}
            if q.is_knockout and q.is_required:
                knockout_failed = True
                entry["knockout_failed"] = True
            details["questions"].append(entry)
            continue

        if not objective:
            # Leave for manual review
            ans.is_correct = None
            ans.points_awarded = None
            ans.save(update_fields=["is_correct", "points_awarded", "updated_at"])
            details["questions"].append(
                {"question_id": str(q.pk), "subjective": True, "points_awarded": None}
            )
            continue

        correct = _answers_match(q.correct_answer, ans.answer, q.question_type)
        pts = float(q.points) if correct else 0.0
        ans.is_correct = correct
        ans.points_awarded = pts
        ans.scored_at = timezone.now()
        ans.save(update_fields=["is_correct", "points_awarded", "scored_at", "updated_at"])
        awarded += pts
        if q.is_knockout and not correct:
            knockout_failed = True
        details["questions"].append(
            {
                "question_id": str(q.pk),
                "correct": correct,
                "points_awarded": pts,
                "knockout": q.is_knockout,
            }
        )

    percent = round((awarded / total_points) * 100, 2) if total_points else None
    passed = None
    if knockout_failed:
        passed = False
    elif percent is not None and assignment.template.passing_score is not None:
        passed = percent >= float(assignment.template.passing_score)

    assignment.score = awarded
    assignment.max_score = total_points
    assignment.score_percent = percent
    assignment.passed = passed
    assignment.knockout_failed = knockout_failed
    assignment.scoring_details = details
    assignment.status = AssessmentAssignment.Status.SCORED
    assignment.scored_at = timezone.now()
    assignment.updated_by = actor
    assignment.save()

    log_action(
        request=request,
        actor=actor,
        organization=assignment.organization,
        action=AuditLog.Action.UPDATE,
        resource_type="AssessmentAssignment",
        resource_id=str(assignment.pk),
        message="Assessment scored",
        metadata={"score_percent": percent, "passed": passed, "knockout_failed": knockout_failed},
    )
    broadcast_to_org(
        assignment.organization_id,
        "assessment.scored",
        {
            "assignment_id": str(assignment.pk),
            "score_percent": percent,
            "passed": passed,
            "knockout_failed": knockout_failed,
        },
    )
    return assignment


@transaction.atomic
def submit_answers(
    assignment: AssessmentAssignment,
    answers: list[dict],
    *,
    actor=None,
    auto_score: bool = True,
    request=None,
) -> AssessmentAssignment:
    """
    answers: [{question_id, answer}]
    """
    if assignment.status in (
        AssessmentAssignment.Status.CANCELLED,
        AssessmentAssignment.Status.EXPIRED,
    ):
        raise ValidationError({"status": "Assignment is no longer open."})
    if assignment.due_at and timezone.now() >= assignment.due_at:
        assignment.status = AssessmentAssignment.Status.EXPIRED
        assignment.save(update_fields=["status", "updated_at"])
        raise ValidationError({"due_at": "Assessment has expired."})

    if assignment.started_at is None:
        assignment.started_at = timezone.now()
        assignment.status = AssessmentAssignment.Status.IN_PROGRESS
        assignment.save(update_fields=["started_at", "status", "updated_at"])

    question_ids = {str(q.pk): q for q in assignment.template.questions.all()}
    for item in answers:
        qid = str(item.get("question_id"))
        question = question_ids.get(qid)
        if not question:
            raise ValidationError({"answers": f"Unknown question {qid}"})
        AssessmentAnswer.objects.update_or_create(
            organization=assignment.organization,
            assignment=assignment,
            question=question,
            defaults={
                "answer": item.get("answer") if "answer" in item else item.get("value", {}),
                "updated_by": actor,
                "created_by": actor,
            },
        )

    # Check required
    answered = set(assignment.answers.values_list("question_id", flat=True))
    missing = [
        str(q.pk)
        for q in question_ids.values()
        if q.is_required and q.pk in answered
    ]
    if missing:
        raise ValidationError({"answers": f"Missing required questions: {missing}"})

    assignment.status = AssessmentAssignment.Status.SUBMITTED
    assignment.submitted_at = timezone.now()
    assignment.updated_by = actor
    assignment.save(update_fields=["status", "submitted_at", "updated_by", "updated_at"])

    if auto_score:
        return score_assignment(assignment, actor=actor, request=request)
    return assignment


def resolve_mentions(body: str, organization) -> list
    """Extract mentioned users from body. Supports @[Name](uuid) or @email."""
    users = []
    seen = set()
    for match in MENTION_RE.finditer(body or ""):
        uuid_id = match.group(2)
        handle = match.group(3)
        user = None
        if uuid_id:
            user = User.objects.filter(pk=uuid_id).first()
        elif handle:
            user = User.objects.filter(email__iexact=handle).first()
            if user is None:
                # Try membership email within org
                from apps.accounts.models import Membership

                membership = (
                    Membership.objects.filter(
                        organization=organization, is_active=True, user__email__iexact=handle
                    )
                    .select_related("user")
                    .first()
                )
                if membership:
                    user = membership.user
        if user and str(user.pk) not in seen:
            seen.add(str(user.pk))
            users.append(user)
    return users


@transaction.atomic
def create_hiring_comment(
    *,
    organization,
    candidate,
    author,
    body: str,
    application=None,
    parent=None,
    request=None,
) -> HiringComment:
    comment = HiringComment.objects.create(
        organization=organization,
        candidate=candidate,
        application=application,
        author=author,
        parent=parent,
        body=body,
        created_by=author,
        updated_by=author,
    )
    mentioned = resolve_mentions(body, organization)
    if mentioned:
        comment.mentions.set(mentioned)
        notify_mentions(comment, mentioned)
    return comment


def notify_mentions(comment: HiringComment, users=None):
    users = users if users is not None else list(comment.mentions.all())
    for user in users:
        if user.pk == comment.author_id:
            break
        notify_user(
            recipient=user,
            title="You were mentioned",
            body=(comment.body[:200] + ("…" if len(comment.body) > 200 else "")),
            organization=comment.organization,
            category="mention",
            link=f"/candidates/{comment.candidate_id}",
            data={
                "comment_id": str(comment.pk),
                "candidate_id": str(comment.candidate_id),
            },
        )
