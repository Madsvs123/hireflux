"""
Compliance URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.compliance.views import (
    ComplianceNoteViewSet,
    ComplianceOverviewView,
    CompliancePolicyViewSet,
    ConsentRecordViewSet,
    DataExportRequestViewSet,
    DataRetentionPolicyViewSet,
    EEODeclarationViewSet,
)

router = DefaultRouter()
router.register(
    r"compliance-policies", CompliancePolicyViewSet, basename="compliance-policy"
)
router.register(r"consent-records", ConsentRecordViewSet, basename="consent-record")
router.register(
    r"retention-policies", DataRetentionPolicyViewSet, basename="retention-policy"
)
router.register(
    r"eeo-declarations", EEODeclarationViewSet, basename="eeo-declaration"
)
router.register(
    r"compliance-notes", ComplianceNoteViewSet, basename="compliance-note"
)
router.register(
    r"data-export-requests", DataExportRequestViewSet, basename="data-export-request"
)

urlpatterns = [
    path("", include(router.urls)),
    path("compliance-overview/", ComplianceOverviewView.as_view(), name="compliance-overview"),
]
