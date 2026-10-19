"""
Sources URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.sources.views import (
    CampaignRecipientViewSet,
    CandidateSourceAttributionViewSet,
    SourceChannelViewSet,
    SourcingCampaignViewSet,
)

router = DefaultRouter()
router.register(r"source-channels", SourceChannelViewSet, basename="source-channel")
router.register(r"sourcing-campaigns", SourcingCampaignViewSet, basename="sourcing-campaign")
router.register(r"campaign-recipients", CampaignRecipientViewSet, basename="campaign-recipient")
router.register(r"source-attributions", CandidateSourceAttributionViewSet, basename="source-attribution")

urlpatterns = [
    path("", include(router.urls)),
]
