"""
WebSocket URL routing.
"""
from django.urls import path

from apps.core.consumers import NotificationConsumer, OrgConsumer

websocket_urlpatterns = [
    path("ws/org/<int:organization_id>/", OrgConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
