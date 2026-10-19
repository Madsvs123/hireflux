"""
Event services: lifecycle, check-in, waitlist, exports, reminders.
"""
from __future__ import annotations

import csv
import io

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.events.models import EventRegistration, EventTask, RecruitingEvent


def _log(request, action, resource_type, resource_id, message, **metadata)
    log_action(
        request=request,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        message=message,
        metadata=metadata,
    )


@transaction.atomic
def publish_event(event: RecruitingEvent, actor=None, request=None) -> RecruitingEvent:
    """Publish a draft event (draft → scheduled)."""
    if event.status == RecruitingEvent.Status.CANCELLED:
        raise ValidationError("A cancelled event cannot be published.")
    event.status = RecruitingEvent.Status.SCHEDULED
    event.updated_by = actor
    event.save()
    _log(request, AuditLog.Action.STATUS_CHANGE, "RecruitingEvent", event.pk, "Event published")
    return event


@transaction.atomic
def cancel_event(event: RecruitingEvent, actor=None, request=None) -> RecruitingEvent:
    """Cancel an event that has not yet been completed."""
    if event.status == RecruitingEvent.Status.COMPLETED:
        raise ValidationError("A completed event cannot be cancelled.")
    event.status = RecruitingEvent.Status.CANCELLED
    event.updated_by = actor
    event.save()
    _log(request, AuditLog.Action.STATUS_CHANGE, "RecruitingEvent", event.pk, "Event cancelled")
    return event


@transaction.atomic
def complete_event(event: RecruitingEvent, actor=None, request=None) -> RecruitingEvent:
    """Mark an event completed (scheduled/ongoing → completed)."""
    if event.status == RecruitingEvent.Status.CANCELLED:
        raise ValidationError("A cancelled event cannot be completed.")
    event.status = RecruitingEvent.Status.COMPLETED
    event.updated_by = actor
    event.save()
    _log(request, AuditLog.Action.STATUS_CHANGE, "RecruitingEvent", event.pk, "Event completed")
    return event


def sync_event_status(event: RecruitingEvent) -> RecruitingEvent:
    """Derive ongoing/completed status from the clock (used by tasks)."""
    if event.status == RecruitingEvent.Status.CANCELLED:
        return event
    now = timezone.now()
    if event.end_at and now >= event.end_at:
        if event.status != RecruitingEvent.Status.COMPLETED:
            event.status = RecruitingEvent.Status.COMPLETED
            event.save(update_fields=["status", "updated_at"])
    elif event.start_at >= now:
        if event.status == RecruitingEvent.Status.SCHEDULED:
            event.status = RecruitingEvent.Status.ONGOING
            event.save(update_fields=["status", "updated_at"])
    return event


@transaction.atomic
def check_in_registration(
    registration: EventRegistration, actor=None, request=None
) -> EventRegistration:
    """Check a registrant in (registered/waitlisted → attended)."""
    if registration.status == EventRegistration.Status.CANCELLED:
        raise ValidationError("A cancelled registration cannot be checked in.")
    if registration.status == EventRegistration.Status.ATTENDED:
        return registration
    registration.status = EventRegistration.Status.ATTENDED
    registration.checked_in_at = timezone.now()
    registration.updated_by = actor
    registration.save()
    _log(
        request,
        AuditLog.Action.STATUS_CHANGE,
        "EventRegistration",
        registration.pk,
        "Registration checked in",
    )
    return registration


@transaction.atomic
def check_in_many(organization, registration_ids: list, actor=None, request=None) -> dict:
    """Batch check-in with per-registration error collection."""
    results = {"checked_in": [], "skipped": [], "errors": []}
    qs = EventRegistration.objects.for_org(organization).filter(pk__in=registration_ids)
    for reg in qs.iterator():
        try:
            check_in_registration(reg, actor=actor, request=request)
            results["checked_in"].append(str(reg.pk))
        except ValidationError as exc:
            results["skipped"].append({"id": str(reg.pk), "reason": exc.detail})
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"id": str(reg.pk), "reason": str(exc)})
    return results


@transaction.atomic
def cancel_registration(
    registration: EventRegistration, actor=None, request=None
) -> EventRegistration:
    """Cancel a registration (registered/attended/waitlisted → cancelled)."""
    if registration.status == EventRegistration.Status.CANCELLED:
        return registration
    registration.status = EventRegistration.Status.CANCELLED
    registration.updated_by = actor
    registration.save()
    _log(
        request,
        AuditLog.Action.STATUS_CHANGE,
        "EventRegistration",
        registration.pk,
        "Registration cancelled",
    )
    return registration


@transaction.atomic
def waitlist_registration(
    registration: EventRegistration, actor=None, request=None
) -> EventRegistration:
    """Move a registration to the waitlist (registered → waitlisted)."""
    if registration.status != EventRegistration.Status.REGISTERED:
        raise ValidationError("Only registered attendees can be moved to the waitlist.")
    registration.status = EventRegistration.Status.WAITLISTED
    registration.updated_by = actor
    registration.save()
    _log(
        request,
        AuditLog.Action.STATUS_CHANGE,
        "EventRegistration",
        registration.pk,
        "Registration waitlisted",
    )
    return registration


@transaction.atomic
def complete_event_task(task: EventTask, actor=None, request=None) -> EventTask:
    """Mark an event task completed."""
    if task.status == EventTask.Status.COMPLETED:
        return task
    if task.status == EventTask.Status.CANCELLED:
        raise ValidationError("A cancelled task cannot be completed.")
    task.status = EventTask.Status.COMPLETED
    task.updated_by = actor
    task.save()
    _log(request, AuditLog.Action.STATUS_CHANGE, "EventTask", task.pk, "Event task completed")
    return task


def export_registrations_csv(event: RecruitingEvent) -> str:
    """Render event registrations as CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "first_name", "last_name", "status", "registered_at", "checked_in_at"])
    qs = EventRegistration.objects.filter(event=event, is_deleted=False).order_by("registered_at")
    for reg in qs.iterator():
        writer.writerow(
            [
                reg.email,
                reg.last_name,
                reg.first_name,
                reg.status,
                reg.registered_at.isoformat() if reg.registered_at else "",
                reg.checked_in_at.isoformat() if reg.checked_in_at else "",
            ]
        )
    return buffer.getvalue()
