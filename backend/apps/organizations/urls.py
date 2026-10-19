from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.organizations.views import (
    DepartmentViewSet,
    HiringTeamMemberViewSet,
    HiringTeamViewSet,
    OfficeViewSet,
    OrganizationViewSet,
)

router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet, basename="organization")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"offices", OfficeViewSet, basename="office")
router.register(r"hiring_teams", HiringTeamViewSet, basename="hiring-team")
router.register(r"hiring-team-members", HiringTeamMemberViewSet, basename="hiring-team-member")

urlpatterns = [
    path("", include(router.urls)),
]
