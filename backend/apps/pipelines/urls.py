"""
Pipelines URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.pipelines.views import (
    ApplicationViewSet,
    AutomatedTaskViewSet,
    BulkActionLogViewSet,
    PipelineStageViewSet,
    PipelineTemplateViewSet,
)

router = DefaultRouter()
router.register(r"pipeline-templates", PipelineTemplateViewSet, basename="pipeline-template")
router.register(r"pipeline-stages", PipelineStageViewSet, basename="pipeline-stage")
router.register(r"applications", ApplicationViewSet, basename="application")
router.register(r"bulk-actions", BulkActionLogViewSet, basename="bulk_actions")
router.register(r"automated_tasks", AutomatedTaskViewSet, basename="automated-task")

urlpatterns = [
    path("", include(router.urls)),
]
