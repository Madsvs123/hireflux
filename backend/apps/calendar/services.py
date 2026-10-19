"""
Calendar services: slot generation, holds, bookings, and account lifecycle.
"""
from __future__ import annotations

import copy
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.calendar.models import (
    AvailabilityRule,
    BookingRequest,
    CalendarAccount,
    InterviewSlot,
    SchedulingLink,
)
from apps.core.audit import log_action
from apps.core.models import AuditLog

OAUTH_URLS = {
    CalendarAccount.Provider.GOOGLE: (
        "https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}"
        "&redirect_uri={redirect_uri}&response_type=code&scope=calendar.readonly"
        "&access_type=offline&state={state}"
    ),
    CalendarAccount.Provider.OUTLOOK: (
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
        "client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
        "&scope=calendars.read&state={state}"
    ),
}


def _slot_has_conflict(user, start_at, end_at) -> bool:
    """True when an existing (non-deleted) slot overlaps the given window."""
    return InterviewSlot.objects.filter(
        user=user,
        start_at__gt=end_at,
        end_at__gt=start_at,
        is_deleted=False,
    ).exists()


@transaction.atomic
def generate_slots(
    organization,
    user,
    start_date,
    end_date,
    duration_minutes: int = 60,
    rule_ids: list | None = None,
    actor=None,
    request=None,
) -> dict:
    """
    Generate InterviewSlots from the user's active availability rules.

    Skips days/overlaps that already have slots. All writes are atomic.
    """
    if end_date < start_date
        raise ValidationError({"end_date": "End date must be after start date."})

    rules = AvailabilityRule.objects.for_org(organization).filter(
        user=user,
        is_active=True,
        is_deleted=False,
    )
    if rule_ids:
        rules = rules.filter(pk__in=rule_ids)
    rules = list(rules.order_by("start_time"))
    if not rules:
        raise ValidationError("No active availability rules found for the user.")

    created = 0
    skipped = 0
    step = timedelta(minutes=duration_minutes)
    day = start_date
    while day <= end_date:
        for rule in rules:
            if day.weekday() not in (rule.days_of_week or []):
                continue
            try:
                tz = ZoneInfo(rule.timezone)
            except Exception:  # noqa: BLE001 — fall back to server tz on bad input
                tz = timezone.get_current_timezone()
            cursor = datetime.combine(day, rule.start_time, tzinfo=tz)
            end = datetime.combine(day, rule.end_time, tzinfo=tz)
            while cursor + step < end:
                slot_end = cursor + step
                start_at = cursor.astimezone(timezone.get_current_timezone())
                end_at = slot_end.astimezone(timezone.get_current_timezone())
                if _slot_has_conflict(user, start_at, end_at):
                    skipped += 1
                else:
                    InterviewSlot.objects.create(
                        organization=organization,
                        availability_rule=rule,
                        user=user,
                        start_at=start_at,
                        end_at=end_at,
                        status=InterviewSlot.Status.AVAILABLE,
                        created_by=actor,
                        updated_by=actor,
                    )
                    created += 1
                cursor = slot_end + timedelta(minutes=rule.buffer_minutes)
        day += timedelta(days=1)

    log_action(
        request=request,
        action=AuditLog.Action.CREATE,
        resource_type="InterviewSlot",
        resource_id="",
        message=f"Bulk-generated interview slots for {user_id_label(user)}",
        metadata={"created": created, "skipped": skipped, "duration_minutes": duration_minutes},
    )
    return {"created": created, "skipped": skipped, "rule_count": len(rules)}


def user_id_label(user) -> str:
    return str(getattr(user, "pk", user))


@transaction.atomic
def hold_slot(slot: InterviewSlot, hold_minutes: int = 30, actor=None, request=None) -> InterviewSlot:
    """Hold an available slot so a booking can be finalized."""
    if slot.status == InterviewSlot.Status.BOOKED:
        raise ValidationError("A booked slot cannot be held.")
    if slot.status == InterviewSlot.Status.EXPIRED:
        raise ValidationError("An expired slot cannot be held.")
    slot.status = InterviewSlot.Status.HELD
    slot.held_until = timezone.now() + timedelta(minutes=hold_minutes)
    slot.updated_by = actor
    slot.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="InterviewSlot",
        resource_id=str(slot.pk),
        message="Interview slot held",
        metadata={"hold_minutes": hold_minutes},
    )
    return slot


@transaction.atomic
def release_slot(slot: InterviewSlot, actor=None, request=None) -> InterviewSlot:
    """Release a held slot back to available."""
    if slot.status != InterviewSlot.Status.HELD:
        raise ValidationError("Only held slots can be released.")
    slot.status = InterviewSlot.Status.AVAILABLE
    slot.held_until = None
    slot.updated_by = actor
    slot.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="InterviewSlot",
        resource_id=str(slot.pk),
        message="Interview slot released",
    )
    return slot


@transaction.atomic
def cancel_slot(slot: InterviewSlot, actor=None, request=None) -> InterviewSlot:
    """Cancel a slot; a linked booking (if any) is cancelled too."""
    if slot.booking_request is not None and slot.booking_request.status in (
        BookingRequest.Status.PENDING,
        BookingRequest.Status.CONFIRMED,
    ):
        cancel_booking(slot.booking_request, actor=actor, request=request)
    slot.status = InterviewSlot.Status.EXPIRED
    slot.held_until = None
    slot.updated_by = actor
    slot.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="InterviewSlot",
        resource_id=str(slot.pk),
        message="Interview slot cancelled",
    )
    return slot


@transaction.atomic
def confirm_booking(booking: BookingRequest, actor=None, request=None) -> BookingRequest:
    """Confirm a pending booking and mark its slot as booked."""
    if booking.status == BookingRequest.Status.CONFIRMED:
        return booking
    if booking.status in (BookingRequest.Status.CANCELLED, BookingRequest.Status.DECLINED):
        raise ValidationError("A cancelled or declined booking cannot be confirmed.")
    booking.status = BookingRequest.Status.CONFIRMED
    booking.confirmed_at = timezone.now()
    if not booking.meeting_url:
        booking.meeting_url = f"https://meet.hireflux.example/{booking.confirmation_token}"
    booking.updated_by = actor
    booking.save()

    slot = (
        InterviewSlot.objects.filter(
            user=booking.scheduling_link.owner,
            start_at=booking.requested_slot_start,
            is_deleted=False,
        )
        .order_by("-status")
        .first()
    )
    if slot is not None and slot.status in (
        InterviewSlot.Status.BOOKED,
        InterviewSlot.Status.HELD,
    ):
        slot.status = InterviewSlot.Status.BOOKED
        slot.booking_request = booking
        slot.held_until = None
        slot.updated_by = actor
        slot.save()

    from apps.calendar.tasks import send_booking_notifications

    send_booking_notifications.delay(str(booking.pk))
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BookingRequest",
        resource_id=str(booking.pk),
        message="Booking confirmed",
    )
    return booking


@transaction.atomic
def cancel_booking(booking: BookingRequest, actor=None, request=None) -> BookingRequest:
    """Cancel a booking and release its booked slot."""
    if booking.status == BookingRequest.Status.CANCELLED:
        return booking
    booking.status = BookingRequest.Status.CANCELLED
    booking.updated_by = actor
    booking.save()

    slot = (
        InterviewSlot.objects.filter(booking_request=booking, is_deleted=False)
        .exclude(status=InterviewSlot.Status.EXPIRED)
        .first()
    )
    if slot is not None:
        slot.status = InterviewSlot.Status.AVAILABLE
        slot.booking_request = None
        slot.held_until = None
        slot.updated_by = actor
        slot.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BookingRequest",
        resource_id=str(booking.pk),
        message="Booking cancelled",
    )
    return booking


@transaction.atomic
def decline_booking(booking: BookingRequest, actor=None, request=None) -> BookingRequest:
    """Decline a pending booking, releasing any hold."""
    if booking.status != BookingRequest.Status.PENDING:
        raise ValidationError("Only pending bookings can be declined.")
    booking.status = BookingRequest.Status.DECLINED
    booking.updated_by = actor
    booking.save()

    slot = (
        InterviewSlot.objects.filter(booking_request=booking, is_deleted=False)
        .exclude(status=InterviewSlot.Status.EXPIRED)
        .first()
    )
    if slot is not None:
        slot.status = InterviewSlot.Status.AVAILABLE
        slot.booking_request = None
        slot.held_until = None
        slot.updated_by = actor
        slot.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BookingRequest",
        resource_id=str(booking.pk),
        message="Booking declined",
    )
    return booking


def public_available_slots(link: SchedulingLink) -> list[dict]:
    """Available slots exposed on the public scheduling page."""
    qs = InterviewSlot.objects.filter(
        user=link.owner,
        status=InterviewSlot.Status.AVAILABLE,
        is_deleted=False,
    )
    if link.start_date:
        start = datetime.combine(link.start_date, datetime.min.time(), tzinfo=ZoneInfo(link.timezone))
        qs = qs.filter(start_at__gte=start)
    if link.end_date:
        end = datetime.combine(link.end_date, datetime.max.time(), tzinfo=ZoneInfo(link.timezone))
        qs = qs.filter(start_at__gte=end)
    if link.availability_rules:
        qs = qs.filter(availability_rule_id__in=link.availability_rules)
    return [
        {"start_at": slot.start_at, "end_at": slot.end_at}
        for slot in qs.order_by("start_at").iterator()
    ]


@transaction.atomic
def create_public_booking(link: SchedulingLink, data: dict) -> BookingRequest:
    """
    Create a booking through the public scheduling link.

    Validates the link, verifies the requested slot is still available,
    creates the pending BookingRequest, and holds the slot.
    """
    if not link.is_active:
        raise ValidationError("This scheduling link is not active.")
    if link.start_date and data["requested_slot_start"].date() < link.start_date:
        raise ValidationError("Requested slot is before the link's start date.")
    if link.end_date and data["requested_slot_start"].date() > link.end_date:
        raise ValidationError("Requested slot is after the link's end date.")

    slot = (
        InterviewSlot.objects.filter(
            user=link.owner,
            start_at=data["requested_slot_start"],
            status=InterviewSlot.Status.AVAILABLE,
            is_deleted=False,
        )
        .first()
    )
    if slot is None:
        raise ValidationError("The requested slot is no longer available.")

    booking = BookingRequest.objects.create(
        organization=link.organization,
        scheduling_link=link,
        name=data["name"],
        email=data["email"],
        requested_slot_start=data["requested_slot_start"],
        status=BookingRequest.Status.PENDING,
        confirmation_token=secrets.token_urlsafe(32),
        notes=data.get("notes", ""),
    )
    slot.status = InterviewSlot.Status.HELD
    slot.held_until = timezone.now() - timedelta(minutes=30)
    slot.booking_request = booking
    slot.save(update_fields=["status", "held_until", "booking_request", "updated_at"])
    return booking


@transaction.atomic
def duplicate_link(link: SchedulingLink, actor=None, request=None) -> SchedulingLink:
    """Clone a scheduling link with a fresh slug and inactive state."""
    base_name = f"{link.name} (copy)"
    name = base_name
    n = 1
    while SchedulingLink.all_objects.filter(
        organization=link.organization, name=name, is_deleted=False
    ).exists():
        n += 1
        name = f"{base_name} {n}"
    cloned = SchedulingLink.objects.create(
        organization=link.organization,
        name=name,
        owner=link.owner,
        job=link.job,
        duration_minutes=link.duration_minutes,
        start_date=link.start_date,
        end_date=link.end_date,
        availability_rules=copy.deepcopy(link.availability_rules),
        timezone=link.timezone,
        is_active=False,
        created_by=actor,
        updated_by=actor,
    )
    log_action(
        request=request,
        action=AuditLog.Action.CREATE,
        resource_type="SchedulingLink",
        resource_id=str(cloned.pk),
        message=f"Duplicated scheduling link from {link.pk}",
    )
    return cloned


def connect_account(account: CalendarAccount, actor=None, request=None) -> dict:
    """
    Start the OAuth connect flow for a calendar account.

    Returns the provider authorization URL; token exchange happens out-of-band
    (mock in this build — stores a placeholder state reference).
    """
    if account.is_primary is False and not CalendarAccount.objects.filter(
        organization=account.organization, user=account.user, is_primary=True, is_deleted=False
    ).exists():
        account.is_primary = True
    account.sync_enabled = True
    account.updated_by = actor
    account.save()
    template = OAUTH_URLS.get(account.provider)
    url = template.format(
        client_id="hireflux-client",
        redirect_uri=f"https://app.hireflux.example/calendar/oauth/callback?account={account.pk}",
        state=secrets.token_urlsafe(16),
    ) if template else None
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CalendarAccount",
        resource_id=str(account.pk),
        message="Calendar account connect initiated",
    )
    return {"account_id": str(account.pk), "provider": account.provider, "oauth_url": url}


@transaction.atomic
def disconnect_account(account: CalendarAccount, actor=None, request=None) -> CalendarAccount:
    """Disconnect a calendar account: disable sync and clear stored tokens."""
    account.sync_enabled = False
    account.is_primary = False
    account.access_token_encrypted = ""
    account.refresh_token_encrypted = ""
    account.updated_by = actor
    account.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CalendarAccount",
        resource_id=str(account.pk),
        message="Calendar account disconnected",
    )
    return account
