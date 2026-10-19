"""
Talent URL routing including public career endpoints.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.talent.views import (
    CareerPageViewSet,
    JobAlertViewSet,
    PublicCareerJobApplyView,
    PublicCareerJobDetailView,
    PublicCareerJobListView,
    PublicCareerPageView,
    ReferralViewSet,
    SavedCandidateViewSet,
    TalentPoolMemberViewSet,
    TalentPoolViewSet,
)

router = DefaultRouter()
router.register(r"talent-pools", TalentPoolViewSet, basename="talent-pool")
router.register(r"talent_pool_members", TalentPoolMemberViewSet, basename="talent-pool-member")
router.register(r"referrals", ReferralViewSet, basename="referral")
router.register(r"career-pages", CareerPageViewSet, basename="career-page")
router.register(r"saved-candidates", SavedCandidateViewSet, basename="saved-candidate")
router.register(r"job-alerts", JobAlertViewSet, basename="job-alert")

urlpatterns = [
    path("", include(router.urls)),
    path("public/careers/<slug:slug>/", PublicCareerPageView.as_view(, name="public-career-page"),
    path(
        "public/careers/<slug:slug>/jobs/",
        PublicCareerJobListView.as_view(),
        name="public-career-jobs",
    ),
    path(
        "public/careers/<slug:slug>/jobs/<str:job_id>/",
        PublicCareerJobDetailView.as_view(),
        name="public-career-job-detail",
    ),
    path(
        "public/careers/<slug:slug>/jobs/<str:job_id>/apply/",
        PublicCareerJobApplyView.as_view(),
        name="public-career-job-apply",
    ),
]
