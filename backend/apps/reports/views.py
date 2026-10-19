"""
Reports ViewSets: definitions, runs, exports, dashboard widgets, live data.
"""
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.reports import services
from apps.reports.models import (
    DashboardWidget,
    ReportDefinition,
    ReportExport,
    ReportRun,
)
from apps.reports.serializers import (
    DashboardWidgetSerializer,
    ReportDefinitionPreviewSerializer,
    ReportDefinitionSerializer,
    ReportExportSerializer,
    ReportRunSerializer,
    WidgetReorderSerializer,
)


class ReportDefinitionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ReportDefinition.objects.all()
    serializer_class = ReportDefinitionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["reports.view"],
        "POST": ["reports.manage"],
        "PUT": ["reports.manage"],
        "PATCH": ["reports.manage"],
        "DELETE": ["reports.manage"],
    }
    filterset_fields = ["report_type", "schedule_enabled", "is_public"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "last_run_at", "report_type"]
    ordering = ["name"]
    audit_resource_type = "ReportDefinition"

    def get_permissions(self):
        action_perms = {
            "run_now": ["reports.manage"],
            "toggle_schedule": ["reports.manage"],
            "preview": ["reports.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="run-now")
    def run_now(self, request, pk=None):
        """Queue a report run for this definition."""
        definition = self.get_object()
        run = services.create_report_run(
            definition, actor=request.user, params=request.data.get("params")
        )
        from apps.reports.tasks import execute_report_run

        execute_report_run.delay(str(run.pk))
        return Response(
            {"queued": True, "run_id": str(run.pk)},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="toggle-schedule")
    def toggle_schedule(self, request, pk=None):
        """Enable/disable the cron schedule."""
        definition = self.get_object()
        enabled = request.data.get("enabled")
        if enabled is not None and not isinstance(enabled, bool)
            raise ValidationError({"enabled": "Must be a boolean."})
        definition = services.toggle_schedule(
            definition, enabled=enabled, actor=request.user
        )
        return Response(ReportDefinitionSerializer(definition).data)

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        """Compute the dataset for this definition without persisting a run."""
        definition = self.get_object()
        ser = ReportDefinitionPreviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        params = ser.validated_data.get("params") or dict(definition.params or {})
        dataset = services.compute_report_dataset(
            request.organization, definition.report_type, params
        )
        return Response({"preview": dataset, "report_type": definition.report_type})


class ReportRunViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ReportRun.objects.select_related("definition", "triggered_by")
    serializer_class = ReportRunSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["reports.view"]}
    filterset_fields = ["definition", "status"]
    search_fields = ["definition__name", "error"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action == "retry":
            self.required_permissions = ["reports.manage"]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Re-queue a failed run."""
        run = self.get_object()
        run = services.retry_report_run(run, actor=request.user)
        return Response(ReportRunSerializer(run).data)


class ReportExportViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ReportExport.objects.select_related("run", "run__definition")
    serializer_class = ReportExportSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["reports.view"]}
    filterset_fields = ["run", "format"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Stream the export file."""
        export = self.get_object()
        if not export.file:
            return Response(
                {"detail": "Export file is not available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        response = FileResponse(export.file.open("rb"))
        response["Content-Disposition"] = (
            f'attachment; filename="{export.file.name.split("/")[-1]}"'
        )
        return response


class DashboardWidgetViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DashboardWidget.objects.all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["reports.view"],
        "POST": ["reports.manage"],
        "PUT": ["reports.manage"],
        "PATCH": ["reports.manage"],
        "DELETE": ["reports.manage"],
    }
    filterset_fields = ["widget_type", "is_visible"]
    search_fields = ["title"]
    ordering = ["position", "title"]
    audit_resource_type = "DashboardWidget"

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Persist the given widget id order."""
        ser = WidgetReorderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        widgets = services.reorder_widgets(
            request.organization,
            ser.validated_data["ordered_ids"],
            actor=request.user,
        )
        return Response(DashboardWidgetSerializer(widgets, many=True).data)


class ReportDataView(APIView):
    """Live aggregated dataset for a supported report type."""

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["reports.manage"]

    def get(self, request, report_type):
        params = {
            "from": request.query_params.get("from") or request.query_params.get("date_from"),
            "to": request.query_params.get("to") or request.query_params.get("date_to"),
            "job_id": request.query_params.get("job"),
        }
        dataset = services.compute_report_dataset(
            request.organization, report_type, {k: v for k, v in params.items() if v}
        )
        return Response(dataset)
