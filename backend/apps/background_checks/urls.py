"""
Background checks URL routing (staff endpoints + provider webhook).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.background_checks.views import (
    BackgroundCheckPackageViewSet,
    BackgroundCheckReportViewSet,
    BackgroundCheckRequestViewSet,
    BackgroundCheckWebhookView,
    CheckDisputeViewSet,
    ScreeningProviderViewSet,
)

router = DefaultRouter()
router.register(
    r"background-check-packages",
    BackgroundCheckPackageViewSet,
    basename="background-check-package",
)
router.register(
    r"background-check-requests",
    BackgroundCheckRequestViewSet,
    basename="background-check-request",
)
router.register(
    r"background-check-reports",
    BackgroundCheckReportViewSet,
    basename="background-check-report",
)
router.register(r"check-disputes", CheckDisputeViewSet, basename="check-dispute")
router.register(
    r"screening-providers", ScreeningProviderViewSet, basename="screening-provider"
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "webhook/background-check/<str:provider_key>/",
        BackgroundCheckWebhookView.as_view(),
        name="background-check-webhook",
    ),
]
