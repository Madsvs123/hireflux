"""
Core URL routes.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.core.views import (
    AuditLogViewSet,
    GlobalSearchView,
    NotificationViewSet,
    health_check,
)

router = DefaultRouter()
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"notification", NotificationViewSet, basename="notification")

urlpatterns = [
    path("health/", health_check, name="health"),
    path("global-search/", GlobalSearchView.as_view(), name="global-search"),
    path("", include(router.urls)),
]
