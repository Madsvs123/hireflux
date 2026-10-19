"""
Background check ViewSets: packages, requests, reports, disputes, providers, webhook.
"""
from django_filters import rest_framework as filters
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.background_checks import services
from apps.background_checks.models import (
    BackgroundCheckPackage,
    BackgroundCheckReport,
    BackgroundCheckRequest,
    CheckDispute,
    ScreeningProvider,
)
from apps.background_checks.serializers import (
    BackgroundCheckPackageSerializer,
    BackgroundCheckReportSerializer,
    BackgroundCheckRequestSerializer,
    CheckDisputeSerializer,
    CreateCheckRequestSerializer,
    CreateDisputeSerializer,
    ResolveDisputeSerializer,
    ReviewReportSerializer,
    ScreeningProviderSerializer,
)
from apps.core.mixins import (
    AuditMixin,
    OrgCreateMixin,
    OrgQuerysetMixin,
    SoftDeleteDestroyMixin,
)
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser

BACKGROUND_CHECKS_PERMISSION_MAP = {
    "SAFE": ["background_checks.view"],
    "POST": ["background_checks.manage"],
    "PUT": ["background_checks.manage"],
    "PATCH": ["background_checks.manage"],
    "DELETE": ["background_checks.manage"],
}


class BackgroundCheckPackageViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = BackgroundCheckPackage.objects.all()
    serializer_class = BackgroundCheckPackageSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = BACKGROUND_CHECKS_PERMISSION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]
    ordering = ["name"]
    audit_resource_type = "BackgroundCheckPackage"


class ScreeningProviderViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ScreeningProvider.objects.all()
    serializer_class = ScreeningProviderSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = BACKGROUND_CHECKS_PERMISSION_MAP
    search_fields = ["name", "api_endpoint"]
    filterset_fields = ["is_active"]
    ordering = ["name"]
    audit_resource_type = "ScreeningProvider"

    def get_permissions(self):
        if self.action == "test":
            self.required_permissions = ["background_checks.view"]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Ping the provider endpoint to verify connectivity."""
        provider = self.get_object()
        return Response(services.test_provider(provider))


class BackgroundCheckRequestFilter(filters.FilterSet):
    candidate = filters.UUIDFilter()
    job = filters.UUIDFilter()
    package = filters.UUIDFilter()
    provider = filters.UUIDFilter()
    status = filters.CharFilter()

    class Meta:
        model = BackgroundCheckRequest
        fields = ["candidate", "job", "package", "provider", "status"]


class BackgroundCheckRequestViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = BackgroundCheckRequest.objects.select_related(
        "candidate", "job", "package", "provider", "initiated_by"
    ).prefetch_related("reports__disputes")
    serializer_class = BackgroundCheckRequestSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = BACKGROUND_CHECKS_PERMISSION_MAP
    filterset_class = BackgroundCheckRequestFilter
    search_fields = [
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
        "provider_ref",
    ]
    ordering = ["-created_at"]
    audit_resource_type = "BackgroundCheckRequest"

    def get_permissions(self):
        action_perms = {
            "submit": ["background_checks.manage"],
            "cancel": ["background_checks.manage"],
            "resend": ["background_checks.manage"],
            "status": ["background_checks.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateCheckRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from apps.candidates.models import Candidate
        from apps.jobs.models import Job

        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response(
                {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        job = None
        if data.get("job_id"):
            job = (
                Job.objects.for_org(request.organization)
                .filter(pk=data["job_id"])
                .first()
            )
            if not job:
                return Response(
                    {"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND
                )

        package = None
        if data.get("package_id"):
            package = (
                BackgroundCheckPackage.objects.for_org(request.organization)
                .filter(pk=data["package_id"])
                .first()
            )
            if not package:
                return Response(
                    {"detail": "Package not found."}, status=status.HTTP_404_NOT_FOUND
                )

        check = BackgroundCheckRequest.objects.create(
            organization=request.organization,
            candidate=candidate,
            job=job,
            package=package,
            status=BackgroundCheckRequest.Status.DRAFT,
            initiated_by=request.user,
            candidate_email=data.get("candidate_email", ""),
            candidate_phone=data.get("candidate_phone", ""),
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            BackgroundCheckRequestSerializer(check).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit the check to the provider (async via Celery)."""
        check = self.get_object()
        check = services.submit_request(check, actor=request.user)
        return Response(BackgroundCheckRequestSerializer(check).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        check = self.get_object()
        check = services.cancel_request(check, actor=request.user)
        return Response(BackgroundCheckRequestSerializer(check).data)

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        """Re-submit the check to the provider."""
        check = self.get_object()
        check = services.resend_request(check, actor=request.user)
        return Response(BackgroundCheckRequestSerializer(check).data)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Status timeline for the check."""
        check = self.get_object()
        return Response(services.build_status_payload(check))


class BackgroundCheckReportViewSet(
    OrgQuerysetMixin,
    AuditMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = BackgroundCheckReport.objects.select_related(
        "request", "reviewed_by"
    ).prefetch_related("disputes")
    serializer_class = BackgroundCheckReportSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["background_checks.view"]}
    filterset_fields = ["request", "status", "reviewed_by"]
    ordering = ["-created_at"]
    audit_resource_type = "BackgroundCheckReport"

    def get_permissions(self):
        if self.action in ("review", "list"):
            self.required_permissions = ["background_checks.manage"]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """Record the review decision (clear / consider / flagged)."""
        report = self.get_object()
        ser = ReviewReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        report = services.review_report(
            report,
            decision=ser.validated_data["decision"],
            summary=ser.validated_data.get("summary", ""),
            findings=ser.validated_data.get("findings", []),
            actor=request.user,
        )
        return Response(BackgroundCheckReportSerializer(report).data)


class CheckDisputeViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = CheckDispute.objects.select_related("report", "candidate", "resolved_by")
    serializer_class = CheckDisputeSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = BACKGROUND_CHECKS_PERMISSION_MAP
    filterset_fields = ["report", "candidate", "status"]
    search_fields = ["reason", "details", "candidate__first_name", "candidate__last_name"]
    ordering = ["-created_at"]
    audit_resource_type = "CheckDispute"

    def get_permissions(self):
        action_perms = {
            "resolve": ["background_checks.manage"],
            "reject": ["background_checks.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from apps.candidates.models import Candidate

        report = (
            BackgroundCheckReport.objects.for_org(request.organization)
            .filter(pk=data["report_id"])
            .first()
        )
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )
        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response(
                {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        dispute = CheckDispute.objects.create(
            organization=request.organization,
            report=report,
            candidate=candidate,
            reason=data["reason"],
            details=data.get("details", ""),
            status=CheckDispute.Status.OPEN,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            CheckDisputeSerializer(dispute).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dispute = services.resolve_dispute(
            dispute,
            resolution=ser.validated_data.get("resolution", ""),
            actor=request.user,
        )
        return Response(CheckDisputeSerializer(dispute).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        dispute = self.get_object()
        ser = ResolveDisputeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        dispute = services.reject_dispute(
            dispute,
            resolution=ser.validated_data.get("resolution", ""),
            actor=request.user,
        )
        return Response(CheckDisputeSerializer(dispute).data)


class BackgroundCheckWebhookView(APIView):
    """
    Anonymous provider callback endpoint.

    Idempotent: posting the same provider_ref twice updates the existing report.
    """

    permission_classes = []
    authentication_classes = []

    def post(self, request, provider_key):
        try:
            result = services.process_provider_callback(provider_key, request.data)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
