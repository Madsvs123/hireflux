"""
Candidate portal URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.portal.views import (
    PortalApplicationViewSet,
    PortalAssessmentViewSet,
    PortalDocumentViewSet,
    PortalInterviewViewSet,
    PortalMeView,
    PortalMessageViewSet,
    PortalOfferViewSet,
)

router = DefaultRouter()
router.register(r"portal/applications", PortalApplicationViewSet, basename="portal-application")
router.register(r"portal/interviews", PortalInterviewViewSet, basename="portal-interview")
router.register(r"portal/assessments", PortalAssessmentViewSet, basename="portal-assessment")
router.register(r"portal/documents", PortalDocumentViewSet, basename="portal-document")
router.register(r"portal/offers", PortalOfferViewSet, basename="portal-offer")
router.register(r"portal/message", PortalMessageViewSet, basename="portal-message")

urlpatterns = [
    path("portal/me/", PortalMeView.as_view(), name="portal-me"),
    path("", include(router.urls)),
]
