"""
Screening URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.screening.views import (
    CandidateJobMatchViewSet,
    ResumeParseResultViewSet,
    ScreeningRunViewSet,
    ScreeningWeightProfileViewSet,
)

router = DefaultRouter()
router.register(r"screening-weights", ScreeningWeightProfileViewSet, basename="screening-weight")
router.register(r"resume_parses", ResumeParseResultViewSet, basename="resume-parse")
router.register(r"candidate-matches", CandidateJobMatchViewSet, basename="candidate-match")
router.register(r"screening-runs", ScreeningRunViewSet, basename="screening-run")

urlpatterns = [
    path("", include(router.urls)),
]
