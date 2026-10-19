"""
Calendar URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.calendar.views import (
    AvailabilityRuleViewSet,
    BookingRequestViewSet,
    CalendarAccountViewSet,
    InterviewSlotViewSet,
    PublicSchedulingBookView,
    PublicSchedulingSlotsView,
    SchedulingLinkViewSet,
)

router = DefaultRouter()
router.register(r"calendar-accounts", CalendarAccountViewSet, basename="calendar-account")
router.register(r"availability-rules", AvailabilityRuleViewSet, basename="availability-rule")
router.register(r"interview-slots", InterviewSlotViewSet, basename="interview-slot")
router.register(r"scheduling-links", SchedulingLinkViewSet, basename="scheduling-link")
router.register(r"booking-requests", BookingRequestViewSet, basename="booking-request")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public/scheduling/<slug:slug>/",
        PublicSchedulingSlotsView.as_view(),
        name="public-scheduling-slots",
    ),
    path(
        "public/scheduling/<slug:slug>/book/",
        PublicSchedulingBookView.as_view(),
        name="public-scheduling-book",
    ),
]
