"""
Automation URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.automation.views import (
    AutomationEventView,
    AutomationRuleViewSet,
    RuleActionLogViewSet,
    RuleExecutionViewSet,
)

router = DefaultRouter()
router.register(r"automation-rules", AutomationRuleViewSet, basename="automation-rule")
router.register(r"rule-executions", RuleExecutionViewSet, basename="rule-execution")
router.register(r"rule-action-logs", RuleActionLogViewSet, basename="rule-action-log")

urlpatterns = [
    path("", include(router.urls)),
    path("automation-events/", AutomationEventView.as_view(), name="automation-events"),
]
