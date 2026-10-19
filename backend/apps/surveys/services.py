"""
Survey services: duplication, sending, submission, analytics aggregation.
"""
from __future__ import annotations

import logging
from collections import Counter
from statistics import mean

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.surveys.models import (
    SurveyInstance,
    SurveyInvitation,
    SurveyQuestion,
    SurveyResponse,
    SurveyTemplate,
)

logger = logging.getLogger(__name__)


def _deliver_email(*, to: str, subject: str, body: str) -> None:
    """
    Email transport seam. Currently logs the message; swap in a real
    SMTP/provider client here without touching callers.
    """
    logger.info("email to=%s subject=%r body=%r", to, subject, body[:200])


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@transaction.atomic
def duplicate_template(template: SurveyTemplate, *, actor=None) -> SurveyTemplate:
    """Copy a template and all its questions."""
    copy = SurveyTemplate.objects.create(
        organization=template.organization,
        name=f"{template.name} (Copy)",
        description=template.description,
        survey_type=template.survey_type,
        is_active=False,
        thank_you_message=template.thank_you_message,
        created_by=actor,
        updated_by=actor,
    )
    for question in template.questions.order_by("order", "created_at"):
        SurveyQuestion.objects.create(
            organization=template.organization,
            template=copy,
            question_text=question.question_text,
            question_type=question.question_type,
            options=question.options,
            is_required=question.is_required,
            order=question.order,
            created_by=actor,
            updated_by=actor,
        )
    return copy


# ---------------------------------------------------------------------------
# Instances & invitations
# ---------------------------------------------------------------------------


@transaction.atomic
def send_instance(instance: SurveyInstance, *, actor=None) -> SurveyInstance:
    """Mark a draft instance as sent and queue invitations."""
    if instance.status != SurveyInstance.Status.DRAFT:
        raise ValidationError({"status": "Only draft instances can be sent."})
    if not instance.invitations.exists():
        raise ValidationError(
            {"invitations": "Add at least one invitation email before sending."}
        )
    instance.status = SurveyInstance.Status.SENT
    instance.sent_at = timezone.now()
    instance.updated_by = actor
    instance.save(update_fields=["status", "sent_at", "updated_at", "updated_by"])
    from apps.surveys.tasks import send_survey_invitations

    send_survey_invitations.delay(str(instance.pk))
    return instance


@transaction.atomic
def send_reminder(instance: SurveyInstance, *, actor=None) -> SurveyInstance:
    """Re-queue unsent/open invitations and send a reminder wave."""
    if instance.status in (
        SurveyInstance.Status.COMPLETED,
        SurveyInstance.Status.EXPIRED,
    ):
        raise ValidationError(
            {"status": f"Cannot remind an instance in status '{instance.status}'."}
        )
    pending = instance.invitations.filter(
        status__in=[
            SurveyInvitation.Status.QUEUED,
            SurveyInvitation.Status.SENT,
            SurveyInvitation.Status.OPENED,
        ],
        is_deleted=False,
    )
    if not pending.exists():
        raise ValidationError({"invitations": "No pending invitations to remind."})
    from apps.surveys.tasks import send_survey_reminders

    send_survey_reminders.delay(str(instance.pk))
    return instance


@transaction.atomic
def close_instance(instance: SurveyInstance, *, actor=None) -> SurveyInstance:
    """Close an open instance (expire) unless already completed."""
    if instance.status == SurveyInstance.Status.COMPLETED:
        raise ValidationError({"status": "A completed instance cannot be closed."})
    instance.status = SurveyInstance.Status.EXPIRED
    instance.updated_by = actor
    instance.save(update_fields=["status", "updated_at", "updated_by"])
    return instance


# ---------------------------------------------------------------------------
# Response submission (public, token-authenticated)
# ---------------------------------------------------------------------------


def get_instance_by_token(token) -> SurveyInstance
    instance = (
        SurveyInstance.objects.filter(token=token, is_deleted=False)
        .select_related("template")
        .first()
    )
    if not instance:
        raise ValidationError({"token": "Invalid or unknown survey token."})
    if instance.status == SurveyInstance.Status.EXPIRED:
        raise ValidationError({"status": "This survey has expired."})
    return instance


def validate_answer(question: SurveyQuestion, answer) -> None:
    """Validate an answer against its question type."""
    if question.question_type == SurveyQuestion.QuestionType.RATING:
        if not isinstance(answer, int) or isinstance(answer, bool):
            raise ValidationError({"answer": "Rating answer must be an integer."})
        if not 1 <= answer < 5:
            raise ValidationError({"answer": "Rating answer must be between 1 and 5."})
    elif question.question_type == SurveyQuestion.QuestionType.CHOICE:
        if not isinstance(answer, str) or answer not in (question.options or []):
            raise ValidationError(
                {"answer": f"Answer must be one of: {', '.join(question.options or [])}."}
            )
    elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
        if not isinstance(answer, bool):
            raise ValidationError({"answer": "Boolean answer must be true or false."})
    else:  # text
        if not isinstance(answer, str) or not answer.strip():
            raise ValidationError({"answer": "Text answer cannot be empty."})


@transaction.atomic
def submit_response(
    instance: SurveyInstance,
    question: SurveyQuestion,
    answer,
) -> SurveyResponse:
    """Record (or update) a single answer and advance instance status."""
    validate_answer(question, answer)

    if question.template_id != instance.template_id:
        raise ValidationError(
            {"question": "Question does not belong to this survey."}
        )

    response, _ = SurveyResponse.objects.update_or_create(
        organization=instance.organization,
        instance=instance,
        question=question,
        defaults={"answer": {"value": answer}},
    )

    if instance.status not in (
        SurveyInstance.Status.SENT,
        SurveyInstance.Status.PARTIALLY_COMPLETED,
    ):
        if instance.status == SurveyInstance.Status.DRAFT:
            instance.status = SurveyInstance.Status.PARTIALLY_COMPLETED
        else:
            raise ValidationError(
                {"status": f"Cannot answer an instance in status '{instance.status}'."}
            )

    questions = SurveyQuestion.objects.filter(
        template=instance.template, is_deleted=False
    )
    answered_ids = set(
        SurveyResponse.objects.filter(instance=instance, is_deleted=False).values_list(
            "question_id", flat=True
        )
    )
    required_ids = set(
        questions.filter(is_required=True).values_list("pk", flat=True)
    )
    all_ids = set(questions.values_list("pk", flat=True))

    if required_ids.issubset(answered_ids) and all_ids.issubset(answered_ids):
        instance.status = SurveyInstance.Status.COMPLETED
        instance.completed_at = timezone.now()
        instance.invitations.filter(
            status__in=[
                SurveyInvitation.Status.SENT,
                SurveyInvitation.Status.OPENED,
                SurveyInvitation.Status.QUEUED,
            ]
        ).update(status=SurveyInvitation.Status.COMPLETED, completed_at=timezone.now())
    elif instance.status == SurveyInstance.Status.SENT:
        instance.status = SurveyInstance.Status.PARTIALLY_COMPLETED

    instance.save(update_fields=["status", "completed_at", "updated_at"])
    return response


def public_survey_payload(instance: SurveyInstance) -> dict:
    """Public-facing survey detail: questions and status (no PII)."""
    questions = (
        SurveyQuestion.objects.filter(template=instance.template, is_deleted=False)
        .order_by("order", "created_at")
        .values("id", "question_text", "question_type", "options", "is_required", "order")
    )
    return {
        "instance_id": str(instance.pk),
        "survey_name": instance.template.name,
        "survey_type": instance.template.survey_type,
        "thank_you_message": instance.template.thank_you_message,
        "status": instance.status,
        "anonymous": instance.anonymous,
        "questions": list(questions),
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def survey_analytics(template: SurveyTemplate) -> dict:
    """Aggregate response rate, ratings, and per-question breakdown."""
    instances = SurveyInstance.objects.filter(template=template, is_deleted=False)
    total_instances = instances.count()
    sent_instances = instances.exclude(status=SurveyInstance.Status.DRAFT).count()
    completed = instances.filter(status=SurveyInstance.Status.COMPLETED).count()
    started = instances.exclude(
        status__in=[
            SurveyInstance.Status.DRAFT,
            SurveyInstance.Status.SENT,
        ]
    ).count()

    questions = SurveyQuestion.objects.filter(template=template, is_deleted=False).order_by(
        "order", "created_at"
    )
    per_question = []
    for question in questions:
        responses = SurveyResponse.objects.filter(
            question=question, is_deleted=False
        )
        values = [r.answer.get("value") for r in responses if isinstance(r.answer, dict)]
        breakdown = {}
        if question.question_type == SurveyQuestion.QuestionType.RATING:
            numeric = [v for v in values if isinstance(v, int)]
            breakdown = {
                "avg_rating": round(mean(numeric), 2) if numeric else None,
                "distribution": {
                    str(star): numeric.count(star) for star in range(1, 6)
                },
            }
        elif question.question_type == SurveyQuestion.QuestionType.CHOICE:
            counts = Counter(values)
            breakdown = {
                "distribution": {str(opt): counts.get(opt, 0) for opt in (question.options or [])}
            }
        elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
            breakdown = {
                "true_count": sum(1 for v in values if v is True),
                "false_count": sum(1 for v in values if v is False),
            }
        else:
            breakdown = {
                "text_response_count": len(values),
                "sample_texts": [str(v)[:200] for v in values[:5]],
            }
        per_question.append(
            {
                "question_id": str(question.pk),
                "question_text": question.question_text,
                "question_type": question.question_type,
                "response_count": len(values),
                "breakdown": breakdown,
            }
        )

    return {
        "template_id": str(template.pk),
        "template_name": template.name,
        "survey_type": template.survey_type,
        "total_instances": total_instances,
        "sent_instances": sent_instances,
        "completed_instances": completed,
        "started_instances": started,
        "response_rate": round(completed / sent_instances * 100, 4) if sent_instances else 0.0,
        "completion_rate": round(completed / sent_instances * 100, 4) if sent_instances else 0.0,
        "questions": per_question,
    }
