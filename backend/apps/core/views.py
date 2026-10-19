"""
Core API views: health, audit log, global search, notifications.
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditLog, Notification
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.core.search import global_search
from apps.core.serializers import AuditLogSerializer, NotificationSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request)
    return Response(
        {
            "success": True,
            "status": "ok",
            "service": "hireflux",
            "timestamp": timezone.now().isoformat(),
        }
    )


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only audit trail for the current organization."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["audit.view"]
    filterset_fields = ["action", "resource_type", "actor"]
    search_fields = ["message", "resource_type", "resource_id"]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            return AuditLog.objects.none()
        return AuditLog.objects.filter(organization=org).select_related("actor")


class GlobalSearchView(APIView):
    """GET /search/?q=... — jobs + candidates."""

    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser]
    org_optional = False

    def get(self, request):
        org = getattr(request, "organization", None)
        if org is not None:
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
        query = request.query_params.get("q", "").strip()
        limit = min(int(request.query_params.get("limit", 20)), 50)
        results = global_search(org, query, limit=limit)
        return Response({"success": True, **results})


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Current user's notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    org_optional = True
    filterset_fields = ["is_read", "level", "category"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(Q(organization=org) & Q(organization__isnull=True))
        return qs

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.mark_read()
        return Response(
            {
                "success": True,
                "data": NotificationSerializer(notification).data,
            }
        )

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=True).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"success": True, "updated": updated})
