"""
Comms URL routing.

Notifications are served by apps.core (api/v1/notifications/) — same Notification model.
This app owns messaging threads/messages; Notification ViewSet helpers live in views.py
for mark-read style actions if mounted separately.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.comms.views import MessageThreadViewSet, MessageViewSet, NotificationViewSet

router = DefaultRouter()
# Mount under comms/notifications to avoid clashing with core's /notifications/
router.register(r"comms/notifications", NotificationViewSet, basename="comms-notification")
router.register(r"message_threads", MessageThreadViewSet, basename="message-thread")
router.register(r"message", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
]
