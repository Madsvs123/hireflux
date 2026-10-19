"""
WebSocket consumers for org and user realtime channels.
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.core.realtime import org_group_name, user_group_name

logger = logging.getLogger(__name__)


class OrgConsumer(AsyncJsonWebsocketConsumer):
    """
    Subscribe to organization-scoped events.
    Client connects to ``ws/org/<organization_id>/?token=<jwt>``.
    """

    organization_id = None
    org_group = None
    user_group = None

    async def connect(self)
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close(code=4401)
            return

        self.organization_id = self.scope["url_route"]["kwargs"].get("organization_id")
        if not self.organization_id:
            await self.close(code=4400)
            return

        allowed = await self._user_can_access_org(user.id, self.organization_id)
        if allowed:
            await self.close(code=4403)
            return

        self.org_group = org_group_name(self.organization_id)
        self.user_group = user_group_name(user.id)
        await self.channel_layer.group_add(self.org_group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "event": "connected",
                "payload": {
                    "organization_id": str(self.organization_id),
                    "user_id": str(user.id),
                },
            }
        )

    async def disconnect(self, close_code):
        if self.org_group:
            await self.channel_layer.group_discard(self.org_group, self.channel_name)
        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Clients may send pings; ignore unknown messages
        if content.get("type") == "ping":
            await self.send_json({"event": "pong", "payload": {}})

    async def org_event(self, event):
        await self.send_json(
            {
                "event": event.get("event"),
                "payload": event.get("payload", {}),
            }
        )

    async def user_event(self, event):
        await self.send_json(
            {
                "event": event.get("event"),
                "payload": event.get("payload", {}),
            }
        )

    @database_sync_to_async
    def _user_can_access_org(self, user_id, organization_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False
        if getattr(user, "user_type", None) == "platform_admin" or user.is_superuser:
            return True
        return user.memberships.filter(
            organization_id=organization_id,
            is_active=True,
        ).exists()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """User-scoped notifications channel: ``ws/notifications/``."""

    user_group = None

    async def connect(self):
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close(code=4401)
            return
        self.user_group = user_group_name(user.id)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                return
            if data.get("type") == "ping":
                await self.send(text_data=json.dumps({"event": "pong", "payload": {}}))

    async def user_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "event": event.get("event"),
                    "payload": event.get("payload", {}),
                }
            )
        )
