"""
HireFlux URL configuration — API v1 + admin.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.offers.urls")),
    path("api/v1/", include("apps.candidates.urls")),
    path("api/v1/", include("apps.pipelines.urls")),
    path("api/v1/", include("apps.screening.urls")),
    path("api/v1/", include("apps.interviews.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.offers.urls")),
    path("api/v1/", include("apps.talent.urls")),
    path("api/v1/", include("apps.comms.url")),
    path("api/v1/", include("apps.portal.urls")),
    path("api/v2/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.onboarding.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.sources.urls")),
    path("api/v1/", include("apps.employer_branding.urls")),
    path("api/v1/", include("apps.events.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.surveys.urls")),
    path("api/v1/", include("apps.integrations.urls")),
    path("api/v1/", include("apps.automation.urls")),
    path("api/v1/", include("apps.calendar.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/", include("apps.compliance.urls")),
    path("api/v1/", include("apps.background_checks.urls")),
    path("api/v1/", include("apps.knowledge_base.urls")),
]
