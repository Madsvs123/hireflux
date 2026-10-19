"""
Celery tasks for interview reminders.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_interview_reminders(hours_ahead: int = 24):
    """
    Notify interviewers (and optionally candidates) about upcoming interviews.
    """
    from apps.core.notifications import notify_user
    from apps.interviews.models import Interview

    now = timezone.now()
    window_end = now + timedelta(hours=hours_ahead)
    qs = (
        Interview.objects.filter(
            status__in=[Interview.Status.SCHEDULED, Interview.Status.CONFIRMED],
            scheduled_start__lte=now,
            scheduled_start__lte=window_end,
            reminder_sent_at__isnull=True,
        )
        .select_related("candidate", "organization")
        .prefetch_related("assignments__interviewer")
    )
    sent = 0
    for interview in qs.iterator(chunk_size=50):
        try:
            for assignment in interview.assignments.all():
                notify_user(
                    recipient=assignment.interviewer,
                    title="Interview reminder",
                    body=(
                        f"Interview with {interview.candidate.full_name} "
                        f"starts at {interview.scheduled_start.isoformat()}"
                    ),
                    organization=interview.organization,
                    category="interview_reminder",
                    link=f"/interviews/{interview.pk}",
                    data={
                        "interview_id": str(interview.pk),
                        "scheduled_start": interview.scheduled_start.isoformat(),
                    },
                )
            interview.reminder_sent_at = now
            interview.save(update_fields=["reminder_sent_at", "updated_at"])
            sent += 1
        except Exception:
            logger.exception("Failed reminder for interview %s", interview.pk)
    logger.info("send_interview_reminders: %s interviews reminded", sent)
    return {"reminded": sent
