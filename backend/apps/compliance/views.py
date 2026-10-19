"""
Compliance ViewSets: policies, consents, retention, EEO, notes, exports, overview.
"""
from django.http import FileResponse
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.compliance import services
from apps.compliance.models import (
    ComplianceNote,
    CompliancePolicy,
    ConsentRecord,
    DataExportRequest,
    DataRetentionPolicy,
    EEODeclaration,
)
from apps.compliance.serializers import (
    ComplianceNoteSerializer,
    CompliancePolicySerializer,
    ConsentRecordSerializer,
    CreateComplianceNoteSerializer,
    CreateEEODeclarationSerializer,
    CreateExportRequestSerializer,
    DataExportRequestSerializer,
    DataRetentionPolicySerializer,
    EEODeclarationSerializer,
    GrantConsentSerializer,
    SubmitEEOSerializer,
)
from apps.core.mixins import (
    AuditMixin,
    OrgCreateMixin,
    OrgQuerysetMixin,
    SoftDeleteDestroyMixin,
)
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser

COMPLIANCE_PERMISSION_MAP = {
    "SAFE": ["compliance.view"],
    "POST": ["compliance.manage"],
    "PUT": ["compliance.manage"],
    "PATCH": ["compliance.manage"],
    "DELETE": ["compliance.manage"],
}


class CompliancePolicyViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = CompliancePolicy.objects.all()
    serializer_class = CompliancePolicySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = COMPLIANCE_PERMISSION_MAP
    search_fields = ["name", "content_html"]
    filterset_fields = ["policy_type", "is_active"]
    ordering = ["-created_at"]
    audit_resource_type = "CompliancePolicy"

    def get_permissions(self):
        if self.action == "activate":
            self.required_permissions = ["compliance.manage"]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate the policy; deactivates siblings and bumps consent versions."""
        policy = self.get_object()
        policy = services.activate_policy(policy, actor=request.user)
        return Response(CompliancePolicySerializer(policy).data)


class ConsentRecordViewSet(
    OrgQuerysetMixin,
    AuditMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = ConsentRecord.objects.select_related("candidate", "user", "policy")
    serializer_class = ConsentRecordSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["compliance.view"]}
    filterset_fields = ["candidate", "user", "policy", "status", "purpose"]
    ordering = ["-granted_at"]
    audit_resource_type = "ConsentRecord"

    def get_permissions(self):
        action_perms = {
            "grant": ["compliance.manage"],
            "withdraw": ["compliance.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def grant(self, request):
        """Grant consent against an active consent policy."""
        ser = GrantConsentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        policy = (
            CompliancePolicy.objects.for_org(request.organization)
            .filter(pk=data["policy_id"])
            .first()
        )
        if not policy:
            return Response(
                {"detail": "Policy not found."}, status=status.HTTP_404_NOT_FOUND
            )

        candidate = None
        if data.get("candidate_id"):
            from apps.candidates.models import Candidate

            candidate = (
                Candidate.objects.for_org(request.organization)
                .filter(pk=data["candidate_id"])
                .first()
            )
            if not candidate:
                return Response(
                    {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
                )

        user = None
        if data.get("user_id"):
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(pk=data["user_id"]).first()

        record = services.grant_consent(
            request.organization,
            policy=policy,
            candidate=candidate,
            user=user,
            purpose=data.get("purpose", ""),
            source=data.get("source", ""),
            ip_address=data.get("ip_address")
            or getattr(request, "client_ip", None),
            actor=request.user,
        )
        return Response(
            ConsentRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        record = self.get_object()
        record = services.withdraw_consent(record, actor=request.user)
        return Response(ConsentRecordSerializer(record).data)


class DataRetentionPolicyViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DataRetentionPolicy.objects.all()
    serializer_class = DataRetentionPolicySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = COMPLIANCE_PERMISSION_MAP
    search_fields = ["data_type", "notes"]
    filterset_fields = ["data_type", "action", "is_active"]
    ordering = ["data_type"]
    audit_resource_type = "DataRetentionPolicy"


class EEODeclarationViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = EEODeclaration.objects.select_related("candidate", "job")
    serializer_class = EEODeclarationSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = COMPLIANCE_PERMISSION_MAP
    filterset_fields = [
        "candidate",
        "job",
        "gender",
        "race_ethnicity",
        "veteran_status",
        "disability_status",
        "is_anonymous",
    ]
    search_fields = [
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
    ]
    ordering = ["-created_at"]
    audit_resource_type = "EEODeclaration"

    def get_permissions(self)
        if self.action == "submit":
            return []
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateEEODeclarationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        candidate = None
        if data.get("candidate_id"):
            from apps.candidates.models import Candidate

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
            from apps.jobs.models import Job

            job = (
                Job.objects.for_org(request.organization)
                .filter(pk=data["job_id"])
                .first()
            )
            if not job:
                return Response(
                    {"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND
                )

        declaration = services.create_declaration(
            request.organization,
            candidate=candidate,
            job=job,
            actor=request.user,
        )
        return Response(
            EEODeclarationSerializer(declaration).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def submit(self, request):
        """Anonymous candidate submission via per-declaration token."""
        ser = SubmitEEOSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        declaration = EEODeclaration.objects.filter(token=data["token"]).first()
        if not declaration:
            return Response(
                {"detail": "Declaration not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if declaration.submitted_at:
            return Response(
                {"detail": "Declaration has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        declaration = services.submit_eeo(
            declaration,
            gender=data.get("gender", ""),
            race_ethnicity=data.get("race_ethnicity", ""),
            veteran_status=data.get("veteran_status", ""),
            disability_status=data.get("disability_status", ""),
            ip_address=getattr(request, "client_ip", None),
        )
        return Response(EEODeclarationSerializer(declaration).data)


class ComplianceNoteViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ComplianceNote.objects.select_related("candidate", "user")
    serializer_class = ComplianceNoteSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = COMPLIANCE_PERMISSION_MAP
    filterset_fields = ["candidate", "user", "category"]
    search_fields = ["body", "candidate__first_name", "candidate__last_name"]
    ordering = ["-created_at"]
    audit_resource_type = "ComplianceNote"

    def create(self, request, *args, **kwargs):
        ser = CreateComplianceNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        candidate = None
        if data.get("candidate_id"):
            from apps.candidates.models import Candidate

            candidate = (
                Candidate.objects.for_org(request.organization)
                .filter(pk=data["candidate_id"])
                .first()
            )
            if not candidate:
                return Response(
                    {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
                )

        note = ComplianceNote.objects.create(
            organization=request.organization,
            candidate=candidate,
            user=request.user,
            category=data.get("category", ComplianceNote.Category.OTHER),
            body=data.get("body", ""),
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            ComplianceNoteSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )


class DataExportRequestViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = DataExportRequest.objects.select_related("candidate", "requested_by")
    serializer_class = DataExportRequestSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = COMPLIANCE_PERMISSION_MAP
    filterset_fields = ["candidate", "status", "requested_by"]
    ordering = ["-requested_at"]
    audit_resource_type = "DataExportRequest"

    def get_permissions(self):
        action_perms = {
            "fulfill": ["compliance.manage"],
            "download": ["compliance.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateExportRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from apps.candidates.models import Candidate

        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response(
                {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        export_request = DataExportRequest.objects.create(
            organization=request.organization,
            candidate=candidate,
            requested_by=request.user,
            status=DataExportRequest.Status.PENDING,
            include_fields=data.get("include_fields", []),
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(
            DataExportRequestSerializer(export_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        """Queue the async data export generation."""
        export_request = self.get_object()
        export_request = services.queue_export_fulfillment(
            export_request, actor=request.user
        )
        return Response(DataExportRequestSerializer(export_request).data)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        export_request = self.get_object()
        if not export_request.export_file:
            return Response(
                {"detail": "Export file is not ready yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            export_request.export_file.open("rb")
        except Exception:  # noqa: BLE001
            return Response(
                {"detail": "Export file could not be opened."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            export_request.export_file,
            as_attachment=True,
            filename=export_request.export_file.name.split("/")[-1],
        )


class ComplianceOverviewView(APIView):
    """Aggregated compliance dashboard for the organization."""

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["compliance.view"]

    def get(self, request):
        return Response(services.compliance_overview(request.organization))
