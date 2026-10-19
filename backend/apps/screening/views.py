"""
Screening ViewSets: weights, parse, match, explanation, re-run.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.screening.models import (
    CandidateJobMatch,
    ResumeParseResult,
    ScreeningRun,
    ScreeningWeightProfile,
)
from apps.screening.serializers import (
    BatchScreenSerializer,
    CandidateJobMatchExplanationSerializer,
    CandidateJobMatchSerializer,
    ExtractTextSerializer,
    ParseResumeSerializer,
    ResumeParseResultSerializer,
    ScreenApplicationSerializer,
    ScreeningRunSerializer,
    ScreeningWeightProfileSerializer,
)
from apps.screening import services


class ScreeningWeightProfileViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ScreeningWeightProfile.objects.all()
    serializer_class = ScreeningWeightProfileSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["screening.view"],
        "POST": ["screening.view"],
        "PUT": ["screening.manage"],
        "PATCH": ["screening.manage"],
        "DELETE": ["screening.manage"],
    }
    search_fields = ["name", "description"]
    ordering = ["name"]
    audit_resource_type = "ScreeningWeightProfile"

    def perform_create(self, serializer):
        org = self.request.organization
        instance = serializer.save(
            organization=org,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        if instance.is_default:
            ScreeningWeightProfile.objects.for_org(org).exclude(pk=instance.pk).update(
                is_default=False
            )

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        if instance.is_default:
            ScreeningWeightProfile.objects.for_org(self.request.organization).exclude(
                pk=instance.pk
            ).update(is_default=False)


class ResumeParseResultViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ResumeParseResult.objects.select_related("document", "candidate")
    serializer_class = ResumeParseResultSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["screening.view"]}
    filterset_fields = ["candidate", "document", "status"]
    ordering = ["-created_at"]

    @action(detail=False, methods=["post"], url_path="parse")
    def parse(self, request)
        """Parse a candidate document (sync or async)."""
        self.required_permissions = ["screening.score"]
        ser = ParseResumeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.candidates.models import CandidateDocument

        doc = (
            CandidateDocument.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["document_id"])
            .first()
        )
        if not doc:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if ser.validated_data.get("async_mode", True):
            from apps.screening.tasks import parse_resume_document

            parse_resume_document.delay(str(doc.pk))
            return Response(
                {"queued": True, "document_id": str(doc.pk)},
                status=status.HTTP_202_ACCEPTED,
            )

        result = services.parse_document(doc, actor=request.user)
        return Response(ResumeParseResultSerializer(result).data)

    @action(detail=False, methods=["post"], url_path="extract")
    def extract(self, request):
        """Run heuristic extraction on raw text (no persistence)."""
        self.required_permissions = ["screening.view"]
        ser = ExtractTextSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        structured = services.extract_resume_structured(
            ser.validated_data["text"],
            extra_skills=ser.validated_data.get("extra_skills"),
        )
        return Response({"structured": structured, "advisory": True})


class CandidateJobMatchFilter(filters.FilterSet):
    job = filters.UUIDFilter()
    candidate = filters.UUIDFilter()
    application = filters.UUIDFilter()
    min_score = filters.NumberFilter(field_name="overall_score", lookup_expr="gte")

    class Meta:
        model = CandidateJobMatch
        fields = ["job", "candidate", "application"]


class CandidateJobMatchViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CandidateJobMatch.objects.select_related(
        "candidate", "job", "application", "weight_profile"
    )
    serializer_class = CandidateJobMatchSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["screening.view"]}
    filterset_class = CandidateJobMatchFilter
    ordering = ["-overall_score"]

    @action(detail=True, methods=["get"])
    def explanation(self, request, pk=None):
        match = self.get_object()
        return Response(CandidateJobMatchExplanationSerializer(match).data)

    @action(detail=False, methods=["post"], url_path="score")
    def score(self, request):
        """Score a candidate against a job (advisory)."""
        self.required_permissions = ["screening.score"]
        ser = ScreenApplicationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        org = request.organization

        application = None
        candidate = None
        job = None

        if data.get("application_id"):
            from apps.pipelines.models import Application

            application = (
                Application.objects.for_org(org)
                .select_related("candidate", "job")
                .filter(pk=data["application_id"])
                .first()
            )
            if not application:
                return Response(
                    {"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND
                )
            candidate = application.candidate
            job = application.job
        else:
            from apps.candidates.models import Candidate
            from apps.jobs.models import Job

            if not data.get("candidate_id") or not data.get("job_id"):
                return Response(
                    {"detail": "Provide application_id or both candidate_id and job_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            candidate = Candidate.objects.for_org(org).filter(pk=data["candidate_id"]).first()
            job = Job.objects.for_org(org).filter(pk=data["job_id"]).first()
            if not candidate or not job:
                return Response(
                    {"detail": "Candidate or job not found."}, status=status.HTTP_404_NOT_FOUND
                )

        profile = None
        if data.get("weight_profile_id"):
            profile = (
                ScreeningWeightProfile.objects.for_org(org)
                .filter(pk=data["weight_profile_id"])
                .first()
            )

        if data.get("async_mode") and application:
            from apps.screening.tasks import screen_application

            screen_application.delay(
                str(application.pk),
                str(profile.pk) if profile else None,
            )
            return Response(
                {
                    "queued": True,
                    "application_id": str(application.pk),
                    "is_recommendation_only": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        run = services.run_screening(
            organization=org,
            application=application,
            candidate=candidate,
            job=job,
            weight_profile=profile,
            actor=request.user,
        )
        return Response(ScreeningRunSerializer(run).data)


class ScreeningRunViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ScreeningRun.objects.select_related(
        "job", "application", "candidate", "match", "weight_profile"
    )
    serializer_class = ScreeningRunSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["screening.view"]}
    filterset_fields = ["job", "application", "candidate", "status", "run_type"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ("rerun", "batch", "screen"):
            self.required_permissions = ["screening.score"]
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def screen(self, request):
        """Trigger screening for an application."""
        ser = ScreenApplicationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        org = request.organization

        from apps.pipelines.models import Application

        application = None
        if data.get("application_id"):
            application = (
                Application.objects.for_org(org)
                .select_related("candidate", "job")
                .filter(pk=data["application_id"])
                .first()
            )
            if not application:
                return Response(
                    {"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND
                )

        profile_id = data.get("weight_profile_id")
        if data.get("async_mode"):
            from apps.screening.tasks import screen_application

            screen_application.delay(str(application.pk), str(profile_id) if profile_id else None)
            return Response({"queued": True, "is_recommendation_only": True}, status=202)

        profile = None
        if profile_id:
            profile = ScreeningWeightProfile.objects.for_org(org).filter(pk=profile_id).first()

        run = services.run_screening(
            organization=org,
            application=application,
            weight_profile=profile,
            actor=request.user,
        )
        return Response(ScreeningRunSerializer(run).data)

    @action(detail=True, methods=["post"])
    def rerun(self, request, pk=None):
        """Re-run screening for the same application/candidate/job."""
        previous = self.get_object()
        run = services.run_screening(
            organization=request.organization,
            application=previous.application,
            candidate=previous.candidate,
            job=previous.job,
            weight_profile=previous.weight_profile,
            actor=request.user,
            run_type=ScreeningRun.RunType.RERUN,
        )
        return Response(ScreeningRunSerializer(run).data)

    @action(detail=False, methods=["post"])
    def batch(self, request):
        """Batch-screen all active applications for a job."""
        ser = BatchScreenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job_id = ser.validated_data["job_id"]
        profile_id = ser.validated_data.get("weight_profile_id")

        from apps.jobs.models import Job

        job = Job.objects.for_org(request.organization).filter(pk=job_id).first()
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        if ser.validated_data.get("async_mode", True):
            from apps.screening.tasks import batch_screen_job

            batch_screen_job.delay(str(job.pk), str(profile_id) if profile_id else None)
            return Response(
                {
                    "queued": True,
                    "job_id": str(job.pk),
                    "is_recommendation_only": True,
                    "never_auto_hire": True,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Sync batch (may be slow)
        from apps.screening.tasks import batch_screen_job as batch_task

        result = batch_task(str(job.pk), str(profile_id) if profile_id else None)
        return Response(result)
