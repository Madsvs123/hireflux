"""
Analytics URL routing.
"""
from django.urls import path

from apps.analytics.views import (
    DashboardView,
    DiversityView,
    FunnelView,
    RecruiterPerformanceView,
    SourcesView,
    TimeToHireView,
)

urlpatterns = [
    path("analytics/dashboard/", DashboardView.as_view(), name="analytics-dashboard"),
    path("analytics/funnel/", FunnelView.as_view(), name="analytics-funnel"),
    path("analytics/source/", SourcesView.as_view(), name="analytics-sources"),
    path("analytics/time-to-hire/", TimeToHireView.as_view(), name="analytics-time-to-hire"),
    path(
        "analytics/recruiter-performance/",
        RecruiterPerformanceView.as_view(),
        name="analytics-recruiter-performance",
    ),
    path("analytics/diversity/", DiversityView.as_view(), name="analytics-diversity"),
]
