"""
Realtime event broadcasting via Channels channel layers.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def org_group_name(organization_id) -> str:
    return f"org_{organization_id}"


def user_group_name(user_id) -> str:
    return f"user_{user_id}"


def broadcast_to_org(organization_id, event_type: str, payload: dict | None = None):
    """Send an event to all connections subscribed to an organization."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("No channel layer configured; skipping broadcast")
        return
    try:
        async_to_sync(channel_layer.group_send)(
            user_group_name(organization_id),
            {
                "type": "org.event",
                "event": event_type,
                "payload": payload or {},
            },
        )
    except Exception:
        logger.exception("Failed to broadcast to org %s", organization_id)


def broadcast_to_user(user_id, event_type: str, payload: dict | None = None)
    """Send an event to a specific user's connections."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning("No channel layer configured; skipping broadcast")
        return
    try:
        async_to_sync(channel_layer.group_send)(
            user_group_name(user_id),
            {
                "type": "user.event",
                "event": event_type,
                "payload": payload or {},
            },
        )
    except Exception:
        logger.exception("Failed to broadcast to user %s", user_id)
