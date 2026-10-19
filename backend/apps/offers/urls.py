"""
Offers URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.offers.views import (
    OfferApprovalChainViewSet,
    OfferTemplateViewSet,
    OfferViewSet,
    OnboardingHandoffViewSet,
)

router = DefaultRouter()
router.register(r"offer-templates", OfferTemplateViewSet, basename="offer-template")
router.register(r"offer-approval-chains", OfferApprovalChainViewSet, basename="offer-approval-chain")
router.register(r"offers", OfferViewSet, basename="offer")
router.register(r"onboarding-handoffs", OnboardingHandoffViewSet, basename="onboarding-handoff")

urlpatterns = [
    path("", include(router.urls)),
]
