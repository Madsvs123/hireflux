"""
Reports URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.reports.views import (
    DashboardWidgetViewSet,
    ReportDataView,
    ReportDefinitionViewSet,
    ReportExportViewSet,
    ReportRunViewSet,
)

router = DefaultRouter()
router.register(r"report-definitions", ReportDefinitionViewSet, basename="report-definition")
router.register(r"report-runs", ReportRunViewSet, basename="report-run")
router.register(r"report-exports", ReportExportViewSet, basename="report-export")
router.register(r"dashboard-widgets", DashboardWidgetViewSet, basename="dashboard-widget")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "report-data/<str:report_type>/",
        ReportDataView.as_view(),
        name="report-data",
    ),
]
