"""
Organization API viewsets.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.mixins import OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.organizations.models import (
    Department,
    HiringTeam,
    HiringTeamMember,
    Office,
    Organization,
)
from apps.organizations.serializers import (
    DepartmentSerializer,
    HiringTeamMemberSerializer,
    HiringTeamSerializer,
    OfficeSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    List orgs the user belongs to; retrieve/update current org details.
    """

    permission_classes = [IsAuthenticated, IsStaffUser]
    org_optional = True
    lookup_field = "pk"
    search_fields = ["name", "slug", "industry"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "user_type", None) == "platform_admin" or user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
        ).distinct()

    def get_permissions(self):
        if self.action in ("create", "list", "retrieve"):
            return [IsAuthenticated(), IsStaffUser()]
        return [IsAuthenticated(), IsOrgMember(), IsStaffUser(), HasPerm()]

    @property
    def required_permissions(self):
        if self.action in ("update", "partial_update"):
            return ["org.edit"]
        if self.action == "destroy":
            return ["org.delete"]
        return []

    def create(self, request, *args, **kwargs)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(
            {
                "success": True,
                "data": OrganizationSerializer(org, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        org = getattr(request, "organization", None)
        if org is None:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "organization_required",
                        "message": "X-Organization-Id header is required.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Ensure membership
        if (
            getattr(request.user, "user_type", None) == "platform_admin"
            or request.user.is_superuser
            or request.user.memberships.filter(organization=org, is_active=True).exists()
        ):
            return Response(
                {
                    "success": False,
                    "error": {"code": "forbidden", "message": "Not a member of this organization."},
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "success": True,
                "data": OrganizationSerializer(org, context={"request": request}).data,
            }
        )


class DepartmentViewSet(OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["org.view"],
        "SAFE": ["org.view"],
        "POST": ["org.view"],
        "PUT": ["org.edit"],
        "PATCH": ["org.edit"],
        "DELETE": ["org.edit"],
    }
    queryset = Department.objects.select_related("parent", "organization")
    search_fields = ["name"]
    filterset_fields = ["parent", "is_active"]
    ordering = ["name"]


class OfficeViewSet(OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, viewsets.ModelViewSet):
    serializer_class = OfficeSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["org.view"],
        "SAFE": ["org.view"],
        "POST": ["org.edit"],
        "PUT": ["org.edit"],
        "PATCH": ["org.edit"],
        "DELETE": ["org.edit"],
    }
    queryset = Office.objects.all()
    search_fields = ["name", "city", "country"]
    filterset_fields = ["is_active", "is_headquarters", "country"]
    ordering = ["name"]


class HiringTeamViewSet(OrgQuerysetMixin, OrgCreateMixin, viewsets.ModelViewSet):
    serializer_class = HiringTeamSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["users.roles"],
        "SAFE": ["users.view"],
        "POST": ["users.edit"],
        "PUT": ["users.edit"],
        "PATCH": ["users.edit"],
        "DELETE": ["users.edit"],
    }
    queryset = HiringTeam.objects.select_related("department").prefetch_related("members__user")
    search_fields = ["name"]
    filterset_fields = ["department", "is_active"]
    ordering = ["name"]


class HiringTeamMemberViewSet(viewsets.ModelViewSet):
    serializer_class = HiringTeamMemberSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["users.view"],
        "SAFE": ["users.view"],
        "POST": ["users.edit"],
        "PUT": ["users.edit"],
        "PATCH": ["users.edit"],
        "DELETE": ["users.edit"],
    }
    queryset = HiringTeamMember.objects.select_related("user", "team")
    filterset_fields = ["team", "role", "is_active", "user"]
    ordering = ["created_at"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        qs = super().get_queryset()
        if org is None:
            return qs.none()
        return qs.filter(team__organization=org)
