"""
Interviews URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.interviews.views import (
    InterviewDecisionSummaryViewSet,
    InterviewerAvailabilityViewSet,
    InterviewKitViewSet,
    InterviewPanelViewSet,
    InterviewViewSet,
    ScorecardViewSet,
)

router = DefaultRouter()
router.register(r"interview-kits", InterviewKitViewSet, basename="interview-kit")
router.register(r"interview-panels", InterviewPanelViewSet, basename="interview-panel")
router.register(r"interviewer-availability", InterviewerAvailabilityViewSet, basename="interviewer-availability")
router.register(r"interviews", InterviewViewSet, basename="interview")
router.register(r"scorecards", ScorecardViewSet, basename="scorecard")
router.register(r"interview-decisions", InterviewDecisionSummaryViewSet, basename="interview-decision")

urlpatterns = [
    path("", include(router.urls)),
]
