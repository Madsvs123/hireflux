"""
Onboarding URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.onboarding.views import (
    OnboardingDocumentViewSet,
    OnboardingPlanTaskViewSet,
    OnboardingPlanViewSet,
    OnboardingTaskDefinitionViewSet,
    OnboardingTemplateViewSet,
)

router = DefaultRouter()
router.register(r"onboarding-templates", OnboardingTemplateViewSet, basename="onboarding-template")
router.register(
    r"onboarding-task-definitions",
    OnboardingTaskDefinitionViewSet,
    basename="onboarding-task-definition",
)
router.register(r"onboarding-plans", OnboardingPlanViewSet, basename="onboarding-plan")
router.register(
    r"onboarding-plan-tasks",
    OnboardingPlanTaskViewSet,
    basename="onboarding-plan-task",
)
router.register(
    r"onboarding-documents",
    OnboardingDocumentViewSet,
    basename="onboarding-document",
)

urlpatterns = [
    path("", include(router.urls)),
]
