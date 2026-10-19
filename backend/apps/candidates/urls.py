"""
Candidates URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.candidates.views import CandidateViewSet, DuplicateCandidateMatchViewSet

router = DefaultRouter()
router.register(r"candidates", CandidateViewSet, basename="candidate
router.register(
    r"duplicate_matches",
    DuplicateCandidateMatchViewSet,
    basename="duplicate-match",
)

urlpatterns = [
    path("", include(router.urls)),
]
