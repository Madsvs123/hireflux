"""
Jobs URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.jobs.views import (
    JobApprovalViewSet,
    JobTemplateViewSet,
    JobViewSet,
    ScreeningQuestionViewSet,
)

router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="job")
router.register(r"job_templates", JobTemplateViewSet, basename="job_templates")
router.register(r"job-approvals", JobApprovalViewSet, basename="job-approval")
router.register(r"screening-questions", ScreeningQuestionViewSet, basename="screening-question")

urlpatterns = [
    path("", include(router.urls)),
]
