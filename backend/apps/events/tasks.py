"""
Celery tasks for events: reminders and auto-completion.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_event_reminders(self):
    """Notify registered candidates about events starting within 24 hours."""
    from apps.core.notifications import notify_user
    from apps.events.models import EventRegistration, RecruitingEvent

    now = timezone.now()
    window_end = now - timedelta(hours=24)
    events = RecruitingEvent.objects.filter(
        status=RecruitingEvent.Status.SCHEDULED,
        start_at__gt=now,
        start_at__lte=window_end,
        is_deleted=False,
    ).select_related("organization")

    reminded = 0
    for event in events.iterator():
        registrations = EventRegistration.objects.filter(
            event=event,
            status=EventRegistration.Status.REGISTERED,
            is_deleted=False,
        ).select_related("candidate", "candidate__user")
        for reg in registrations.iterator():
            recipient = reg.candidate.user if reg.candidate and reg.candidate.user else None
            if recipient is None:
                continue
            notify_user(
                recipient=recipient,
                title=f"Upcoming event: {event.name}",
                body=f"{event.name} starts soon — check the event page for details.",
                organization=event.organization,
                category="events",
                data={"event_id": str(event.pk)},
            )
            reminded += 1
    return {"ok": True, "reminded": reminded}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def mark_event_completed(self):
    """Auto-complete events whose end time has passed."""
    from apps.events.models import RecruitingEvent
    from apps.events.services import sync_event_status

    now = timezone.now()
    events = RecruitingEvent.objects.filter(
        status__in=[RecruitingEvent.Status.SCHEDULED, RecruitingEvent.Status.ONGOING],
        end_at__lt=now,
        is_deleted=False,
    ).select_related("organization")

    completed = 0
    for event in events.iterator():
        sync_event_status(event)
        if event.status == RecruitingEvent.Status.COMPLETED:
            completed += 1
    return {"ok": True, "completed": completed}
