"""
Job ViewSets with lifecycle actions and nested questions/recruiters.
"""
from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.jobs.models import Job, JobApproval, JobRecruiter, JobTemplate, ScreeningQuestion
from apps.jobs.serializers import (
    CreateFromTemplateSerializer,
    JobApprovalSerializer,
    JobLifecycleSerializer,
    JobListSerializer,
    JobRecruiterSerializer,
    JobSerializer,
    JobTemplateSerializer,
    ScreeningQuestionSerializer,
)
from apps.jobs import services

User = get_user_model()


class JobFilter(filters.FilterSet):
    status = filters.CharFilter()
    employment_type = filters.CharFilter()
    experience_level = filters.CharFilter()
    department = filters.UUIDFilter()
    office = filters.CharFilter()
    hiring_manager = filters.UUIDFilter()
    remote_policy = filters.CharFilter()
    career_page_visible = filters.BooleanFilter()

    class Meta:
        model = Job
        fields = [
            "status",
            "employment_type",
            "experience_level",
            "department",
            "office",
            "hiring_manager",
            "remote_policy",
            "career_page_visible",
        ]


class JobViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = Job.objects.select_related(
        "department", "office", "hiring_manager", "pipeline_template"
    ).prefetch_related("screening_questions", "recruiters", "approvals")
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["jobs.view"],
        "POST": ["jobs.create"],
        "PUT": ["jobs.edit"],
        "PATCH": ["jobs.edit"],
        "DELETE": ["jobs.view"],
    }
    filterset_class = JobFilter
    search_fields = ["title", "slug", "description", "required_skill"]
    ordering_fields = ["created_at", "published_at", "title", "status", "closes_at"]
    ordering = ["-created_at"]
    audit_resource_type = "Job"

    def get_serializer_class(self):
        if self.action != "list":
            return JobListSerializer
        return JobSerializer

    def get_permissions(self):
        action_perms = {
            "publish": ["jobs.publish"],
            "submit_approval": ["jobs.edit"],
            "approve": ["jobs.publish"],
            "reject": ["jobs.publish"],
            "pause": ["jobs.edit"],
            "close": ["jobs.close"],
            "from_template": ["jobs.create"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None)
        job = self.get_object()
        ser = JobLifecycleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = services.publish_job(job, actor=request.user, request=request)
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        job = self.get_object()
        ser = JobLifecycleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        approver = None
        approver_id = ser.validated_data.get("approver")
        if approver_id:
            approver = User.objects.filter(pk=approver_id).first()
        job, approval = services.submit_for_approval(
            job,
            actor=request.user,
            approver=approver,
            comment=ser.validated_data.get("comment", ""),
            request=request,
        )
        return Response(
            {
                "job": JobSerializer(job).data,
                "approval": JobApprovalSerializer(approval).data,
            }
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        job = self.get_object()
        ser = JobLifecycleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = services.approve_job(
            job,
            actor=request.user,
            comment=ser.validated_data.get("comment", ""),
            request=request,
            publish=ser.validated_data.get("publish", True),
        )
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        job = self.get_object()
        ser = JobLifecycleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = services.reject_job(
            job,
            actor=request.user,
            comment=ser.validated_data.get("comment", ""),
            request=request,
        )
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        job = self.get_object()
        job = services.pause_job(job, actor=request.user, request=request)
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        job = self.get_object()
        ser = JobLifecycleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = services.close_job(
            job,
            actor=request.user,
            request=request,
            archive=ser.validated_data.get("archive", False),
        )
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=["get", "post"], url_path="questions")
    def questions(self, request, pk=None):
        job = self.get_object()
        if request.method == "GET":
            qs = job.screening_questions.all()
            return Response(ScreeningQuestionSerializer(qs, many=True).data)
        ser = ScreeningQuestionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = ScreeningQuestion.objects.create(
            organization=job.organization,
            job=job,
            created_by=request.user,
            updated_by=request.user,
            **ser.validated_data,
        )
        return Response(ScreeningQuestionSerializer(question).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"questions/(?P<question_id>[^/.]+)",
    )
    def question_detail(self, request, pk=None, question_id=None):
        job = self.get_object()
        question = job.screening_questions.filter(pk=question_id).first()
        if not question:
            return Response({"detail": "Question not found."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "DELETE":
            question.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = ScreeningQuestionSerializer(question, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user)
        return Response(ser.data)

    @action(detail=True, methods=["get", "post"], url_path="recruiters")
    def recruiters(self, request, pk=None):
        job = self.get_object()
        if request.method == "GET":
            qs = job.recruiters.select_related("user").all()
            return Response(JobRecruiterSerializer(qs, many=True).data)
        ser = JobRecruiterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        recruiter = JobRecruiter.objects.create(
            organization=job.organization,
            job=job,
            created_by=request.user,
            updated_by=request.user,
            **ser.validated_data,
        )
        if recruiter.is_primary:
            JobRecruiter.objects.filter(job=job).exclude(pk=recruiter.pk).update(is_primary=False)
        return Response(JobRecruiterSerializer(recruiter).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"recruiters/(?P<recruiter_id>[^/.]+)",
    )
    def recruiter_detail(self, request, pk=None, recruiter_id=None):
        job = self.get_object()
        recruiter = job.recruiters.filter(pk=recruiter_id).first()
        if not recruiter:
            return Response({"detail": "Recruiter not found."}, status=status.HTTP_404_NOT_FOUND)
        if request.method == "DELETE":
            recruiter.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = JobRecruiterSerializer(recruiter, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user)
        if not ser.instance.is_primary:
            JobRecruiter.objects.filter(job=job).exclude(pk=ser.instance.pk).update(is_primary=False)
        return Response(ser.data)

    @action(detail=False, methods=["post"], url_path="from-template")
    def from_template(self, request):
        ser = CreateFromTemplateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        org = request.organization
        template = JobTemplate.objects.for_org(org).filter(pk=ser.validated_data["template_id"]).first()
        if not template:
            return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        overrides = {}
        if ser.validated_data.get("title"):
            overrides["title"] = ser.validated_data["title"]
        if ser.validated_data.get("department"):
            overrides["department_id"] = ser.validated_data["department"]
        if ser.validated_data.get("office"):
            overrides["office_id"] = ser.validated_data["office"]
        job = services.create_job_from_template(
            template, organization=org, actor=request.user, overrides=overrides
        )
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


class JobTemplateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = JobTemplate.objects.all()
    serializer_class = JobTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["jobs.view"],
        "POST": ["jobs.create"],
        "PUT": ["jobs.edit"],
        "PATCH": ["jobs.edit"],
        "DELETE": ["jobs.delete"],
    }
    search_fields = ["name", "title_template", "description"]
    ordering = ["name"]
    audit_resource_type = "JobTemplate"


class JobApprovalViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = JobApproval.objects.select_related("job", "requested_by", "approver", "decided_by")
    serializer_class = JobApprovalSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["jobs.view"]}
    filterset_fields = ["job", "status", "approver"]
    ordering = ["-created_at"]


class ScreeningQuestionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = ScreeningQuestion.objects.select_related("job")
    serializer_class = ScreeningQuestionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["jobs.view", "screening.view"],
        "POST": ["jobs.edit", "screening.manage"],
        "PUT": ["jobs.edit", "screening.manage"],
        "PATCH": ["jobs.edit", "screening.manage"],
        "DELETE": ["jobs.edit", "screening.manage"],
    }
    filterset_fields = ["job", "is_knockout", "question_type"]
    ordering = ["order"]
    audit_resource_type = "ScreeningQuestion"

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        job = serializer.validated_data.get("job")
        job_id = self.request.data.get("job")
        if job is None and job_id:
            job = Job.objects.for_org(self.request.organization).filter(pk=job_id).first()
        if job is None:
            raise ValidationError({"job": "Job is required."})
        serializer.save(
            organization=self.request.organization,
            job=job,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
