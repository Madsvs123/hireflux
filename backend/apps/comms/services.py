"""
Notification and messaging services.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

# Prefer core notify; re-export for comms consumers
from apps.core.notifications import notify_user  # noqa: F401
from apps.core.realtime import broadcast_to_user
from apps.comms.models import Message, MessageParticipant, MessageThread


@transaction.atomic
def send_message(
    *,
    organization,
    sender,
    body: str,
    thread: MessageThread | None = None,
    subject: str = "",
    participant_ids: list | None = None,
    candidate=None,
    application=None,
    job=None,
    thread_type: str = MessageThread.ThreadType.GENERAL,
    body_html: str = "",
    attachments: list | None = None,
    notify: bool = True,
) -> tuple[MessageThread, Message]:
    if not body and not str(body).strip():
        raise ValidationError({"body": "Message body is required."})

    if thread is None:
        thread = MessageThread.objects.create(
            organization=organization,
            subject=subject or "",
            thread_type=thread_type,
            candidate=candidate,
            application=application,
            job=job or (application.job if application else None),
            created_by=sender,
            updated_by=sender,
        )
        # Ensure sender is a participant
        MessageParticipant.objects.get_or_create(
            organization=organization,
            thread=thread,
            user=sender,
            defaults={
                "role": (
                    MessageParticipant.Role.CANDIDATE
                    if getattr(sender, "user_type", None) == "candidate"
                    else MessageParticipant.Role.STAFF
                ),
            },
        )
        for uid in participant_ids or []:
            if str(uid) == str(sender.pk):
                continue
            MessageParticipant.objects.get_or_create(
                organization=organization,
                thread=thread,
                user_id=uid,
                defaults={"role": MessageParticipant.Role.STAFF},
            )
        if candidate and candidate.user_id:
            MessageParticipant.objects.get_or_create(
                organization=organization,
                thread=thread,
                user_id=candidate.user_id,
                defaults={"role": MessageParticipant.Role.CANDIDATE},
            )
    else:
        if thread.organization_id != organization.pk:
            raise ValidationError({"thread": "Thread does not belong to organization."})
        # Auto-join sender
        MessageParticipant.objects.get_or_create(
            organization=organization,
            thread=thread,
            user=sender,
            defaults={
                "role": (
                    MessageParticipant.Role.CANDIDATE
                    if getattr(sender, "user_type", None) == "candidate"
                    else MessageParticipant.Role.STAFF
                ),
            },
        )

    message = Message.objects.create(
        organization=organization,
        thread=thread,
        sender=sender,
        body=body,
        body_html=body_html or "",
        attachments=attachments or [],
        created_by=sender,
        updated_by=sender,
    )
    thread.last_message_at = message.created_at
    thread.updated_by = sender
    thread.save(update_fields=["last_message_at", "updated_by", "updated_at"])

    if notify:
        for participant in thread.participants.select_related("user").filter(user=sender):
            if participant.is_muted:
                continue
            from apps.core.notifications import notify_user as _notify

            _notify(
                recipient=participant.user,
                title=thread.subject or "New message",
                body=body[:200],
                organization=organization,
                category="message",
                link=f"/messages/{thread.pk}",
                data={"thread_id": str(thread.pk), "message_id": str(message.pk)},
            )
            try:
                broadcast_to_user(
                    participant.user_id,
                    "message.new",
                    {
                        "thread_id": str(thread.pk),
                        "message_id": str(message.pk),
                        "body_preview": body[:120],
                    },
                )
            except Exception:
                pass

    return thread, message


def mark_thread_read(thread: MessageThread, user) -> MessageParticipant | None:
    participant = thread.participants.filter(user=user).first()
    if not participant:
        return None
    participant.last_read_at = timezone.now()
    participant.save(update_fields=["last_read_at"])
    return participant
