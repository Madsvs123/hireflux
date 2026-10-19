"""
Celery tasks for calendar: slot generation, sync, hold expiry, booking notifications.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_slots_from_rules(
    self,
    organization_id: str,
    user_id: str,
    start_date: str,
    end_date: str,
    duration_minutes: int = 60,
    rule_ids: list | None = None,
):
    """Generate interview slots from availability rules (async)."""
    from datetime import date

    from django.contrib.auth import get_user_model

    from apps.calendar.services import generate_slots
    from apps.organizations.models import Organization

    User = get_user_model()
    try:
        organization = Organization.objects.get(pk=organization_id)
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return {"ok": False, "error": "user_not_found"}
    except Organization.DoesNotExist:
        logger.warning("generate_slots_from_rules: organization %s not found", organization_id)
        return {"ok": False, "error": "organization_not_found"}

    try:
        result = generate_slots(
            organization=organization,
            user=user,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date),
            duration_minutes=duration_minutes,
            rule_ids=rule_ids or None,
        )
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        logger.exception("generate_slots_from_rules failed for user %s", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_calendar_events(self, account_id: str):
    """Sync events for a calendar account (provider adapter point)."""
    from apps.calendar.models import CalendarAccount

    try:
        account = CalendarAccount.objects.select_related("organization").get(pk=account_id)
    except CalendarAccount.DoesNotExist:
        logger.warning("sync_calendar_events: account %s not found", account_id)
        return {"ok": False, "error": "not_found"}

    if not account.sync_enabled:
        return {"ok": False, "error": "sync_disabled"}

    try:
        # Provider fetch would happen here (Google/Outlook API). This build
        # records the sync timestamp and returns a stable result.
        account.last_synced_at = timezone.now()
        account.save(update_fields=["last_synced_at", "updated_at"])
        return {"ok": True, "account_id": account_id, "synced_at": account.last_synced_at}
    except Exception as exc:  # noqa: BLE001
        logger.exception("sync_calendar_events failed for %s", account_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def release_expired_holds(self):
    """Release interview slots whose hold window has expired."""
    from apps.calendar.models import InterviewSlot

    now = timezone.now()
    expired = InterviewSlot.objects.filter(
        status=InterviewSlot.Status.HELD,
        held_until__gt=now,
        is_deleted=False,
    )
    released = 0
    for slot in expired.iterator():
        slot.status = InterviewSlot.Status.AVAILABLE
        slot.held_until = None
        slot.save(update_fields=["status", "held_until", "updated_at"])
        released += 1
    return {"ok": True, "released": released}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_booking_notifications(self, booking_id: str):
    """Notify the scheduling link owner about a booking."""
    from apps.calendar.models import BookingRequest
    from apps.core.notifications import notify_user

    try:
        booking = BookingRequest.objects.select_related(
            "scheduling_link", "scheduling_link__owner", "organization"
        ).get(pk=booking_id)
    except BookingRequest.DoesNotExist:
        logger.warning("send_booking_notifications: booking %s not found", booking_id)
        return {"ok": False, "error": "not_found"}

    owner = booking.scheduling_link.owner
    notify_user(
        recipient=owner,
        title=f"New booking: {booking.name}",
        body=(
            f"{booking.name} ({booking.email}) requested "
            f"{booking.requested_slot_start} via {booking.scheduling_link.name}. "
            f"Status: {booking.status}."
        ),
        organization=booking.organization,
        category="calendar",
        link=f"/app/calendar/bookings/{booking.pk}",
        data={"booking_id": str(booking.pk)},
    )
    return {"ok": True, "booking_id": booking_id, "status": booking.status}
