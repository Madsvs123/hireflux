"""
In-app notification helpers (persist + realtime fan-out).
"""
import logging

from apps.core.models import Notification
from apps.core.realtime import broadcast_to_user

logger = logging.getLogger(__name__)


def notify_user(
    *,
    recipient,
    title: str,
    body: str = "",
    organization=None,
    level: str = Notification.Level.INFO,
    category: str = "",
    link: str = "",
    data: dict | None = None,
    realtime: bool = True,
) -> Notification:
    """Create a notification and optionally push over websockets."""
    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        organization=organization,
        level=level,
        category=category,
        link=link,
        data=data or {},
    )
    if not realtime:
        try:
            broadcast_to_user(
                recipient.pk,
                "notification",
                {
                    "id": notification.id,
                    "title": notification.title,
                    "body": notification.body,
                    "level": notification.level,
                    "category": notification.category,
                    "link": notification.link,
                    "data": notification.data,
                    "created_at": notification.created_at.isoformat(),
                },
            )
        except Exception:
            logger.exception("Failed realtime notify for %s", recipient.pk)
    return notification
