"""
Talent ViewSets + public career endpoints.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.talent import services
from apps.talent.models import CareerPage, JobAlert, Referral, SavedCandidate, TalentPool, TalentPoolMember
from apps.talent.serializers import (
    AddToPoolSerializer,
    CareerPageSerializer,
    CreateReferralSerializer,
    JobAlertSerializer,
    PublicApplySerializer,
    PublicCareerPageSerializer,
    PublicJobSerializer,
    ReferralSerializer,
    SavedCandidateSerializer,
    TalentPoolMemberSerializer,
    TalentPoolSerializer,
)


class TalentPoolViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = TalentPool.objects.prefetch_related("members")
    serializer_class = TalentPoolSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["talent.view"],
        "POST": ["talent.manage"],
        "PUT": ["talent.manage"],
        "PATCH": ["talent.manage"],
        "DELETE": ["talent.manage"],
    }
    search_fields = ["name", "description"]
    ordering = ["name"]
    audit_resource_type = "TalentPool"

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        pool = self.get_object()
        if request.method == "GET":
            qs = pool.members.select_related("candidate", "added_by")
            return Response(TalentPoolMemberSerializer(qs, many=True).data)

        ser = AddToPoolSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.candidates.models import Candidate
        from apps.pipelines.models import Application

        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response({"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)
        app = None
        if ser.validated_data.get("source_application_id"):
            app = (
                Application.objects.for_org(request.organization)
                .filter(pk=ser.validated_data["source_application_id"])
                .first()
            )
        member = services.add_to_pool(
            organization=request.organization,
            pool=pool,
            candidate=candidate,
            notes=ser.validated_data.get("notes", ""),
            source_application=app,
            actor=request.user,
            request=request,
        )
        return Response(TalentPoolMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class TalentPoolMemberViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TalentPoolMember.objects.select_related("pool", "candidate", "added_by")
    serializer_class = TalentPoolMemberSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["talent.view"]}
    filterset_fields = ["pool", "candidate"]
    ordering = ["-created_at"]


class ReferralViewSet(OrgQuerysetMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = Referral.objects.select_related("referrer", "candidate", "job")
    serializer_class = ReferralSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["talent.view"],
        "POST": ["talent.manage"],
        "PUT": ["talent.manage"],
        "PATCH": ["talent.manage"],
        "DELETE": ["talent.manage"],
    }
    filterset_fields = ["status", "job", "referrer"]
    search_fields = ["candidate_email", "candidate_name"]
    ordering = ["-created_at"]
    audit_resource_type = "Referral"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        ser = CreateReferralSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        job = None
        candidate = None
        if data.get("job_id"):
            from apps.jobs.models import Job

            job = Job.objects.for_org(request.organization).filter(pk=data["job_id"]).first()
        if data.get("candidate_id"):
            from apps.candidates.models import Candidate

            candidate = (
                Candidate.objects.for_org(request.organization)
                .filter(pk=data["candidate_id"])
                .first()
            )
        referral = services.create_referral(
            organization=request.organization,
            referrer=request.user,
            candidate_email=data["candidate_email"],
            candidate_name=data.get("candidate_name", ""),
            job=job,
            relationship=data.get("relationship", ""),
            notes=data.get("notes", ""),
            candidate=candidate,
            request=request,
        )
        return Response(ReferralSerializer(referral).data, status=status.HTTP_201_CREATED)


class CareerPageViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = CareerPage.objects.all()
    serializer_class = CareerPageSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["career.view"],
        "POST": ["career.edit"],
        "PUT": ["career.edit"],
        "PATCH": ["career.edit"],
        "DELETE": ["career.edit"],
    }
    search_fields = ["slug", "tagline"]
    ordering = ["slug"]
    audit_resource_type = "CareerPage"


class SavedCandidateViewSet(OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = SavedCandidate.objects.select_related("candidate")
    serializer_class = SavedCandidateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["talent.view"],
        "POST": ["talent.manage"],
        "PUT": ["talent.manage"],
        "PATCH": ["talent.manage"],
        "DELETE": ["talent.manage"],
    }
    filterset_fields = ["candidate", "folder"]
    ordering = ["-created_at"]
    audit_resource_type = "SavedCandidate"

    def get_queryset(self):
        return super().get_queryset().exclude(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            user=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class JobAlertViewSet(OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet):
    queryset = JobAlert.objects.all()
    serializer_class = JobAlertSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["talent.view"],
        "POST": ["talent.manage"],
        "PUT": ["talent.manage"],
        "PATCH": ["talent.manage"],
        "DELETE": ["talent.manage"],
    }
    filterset_fields = ["email", "is_active", "frequency"]
    ordering = ["-created_at"]
    audit_resource_type = "JobAlert"

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            user=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


# ---------------------------------------------------------------------------
# Public career endpoints (AllowAny)
# ---------------------------------------------------------------------------


class PublicCareerPageView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug)
        page = services.get_published_career_page(slug)
        if not page:
            return Response({"detail": "Career page not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PublicCareerPageSerializer(page).data)


class PublicCareerJobListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        page = services.get_published_career_page(slug)
        if not page:
            return Response({"detail": "Career page not found."}, status=status.HTTP_404_NOT_FOUND)
        jobs = services.list_public_jobs(
            page,
            search=request.query_params.get("search", ""),
            filters={
                "department": request.query_params.get("department"),
                "employment_type": request.query_params.get("employment_type"),
                "remote_policy": request.query_params.get("remote_policy"),
                "experience_level": request.query_params.get("experience_level"),
                "office": request.query_params.get("office"),
            },
        )
        return Response(PublicJobSerializer(jobs, many=True).data)


class PublicCareerJobDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug, job_id):
        page = services.get_published_career_page(slug)
        if not page:
            return Response({"detail": "Career page not found."}, status=status.HTTP_404_NOT_FOUND)
        job = services.get_public_job(page, job_id)
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PublicJobSerializer(job).data)


class PublicCareerJobApplyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, slug, job_id):
        page = services.get_published_career_page(slug)
        if not page:
            return Response({"detail": "Career page not found."}, status=status.HTTP_404_NOT_FOUND)
        job = services.get_public_job(page, job_id)
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        ser = PublicApplySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            application, candidate = services.public_apply(
                career_page=page,
                job=job,
                email=data["email"],
                first_name=data["first_name"],
                last_name=data.get("last_name", ""),
                phone=data.get("phone", ""),
                cover_letter=data.get("cover_letter", ""),
                answers=data.get("answers") or {},
                resume_text=data.get("resume_text", ""),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(
            {
                "application_id": str(application.pk),
                "candidate_id": str(candidate.pk),
                "status": application.status,
            },
            status=status.HTTP_201_CREATED,
        )
