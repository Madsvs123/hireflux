"""
Events URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.events.views import (
    EventRegistrationViewSet,
    EventSessionViewSet,
    EventTaskViewSet,
    RecruitingEventViewSet,
)

router = DefaultRouter()
router.register(r"events", RecruitingEventViewSet, basename="event")
router.register(r"event-sessions", EventSessionViewSet, basename="event-session")
router.register(r"event-registrations", EventRegistrationViewSet, basename="event-registration")
router.register(r"event-tasks", EventTaskViewSet, basename="event-task")

urlpatterns = [
    path("", include(router.urls)),
]
