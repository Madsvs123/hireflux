"""
Assessment ViewSets: templates, questions, assignments, ratings, comments.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.assessments import services
from apps.assessments.models import (
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)
from apps.assessments.serializers import (
    AssessmentAssignmentSerializer,
    AssessmentQuestionSerializer,
    AssessmentTemplateSerializer,
    AssignAssessmentSerializer,
    CandidateRatingSerializer,
    CreateHiringCommentSerializer,
    HiringCommentSerializer,
    SubmitAnswersSerializer,
)
from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class AssessmentTemplateViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = AssessmentTemplate.objects.prefetch_related("questions")
    serializer_class = AssessmentTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["assessments.view"],
        "POST": ["assessments.manage"],
        "PUT": ["assessments.manage"],
        "PATCH": ["assessments.manage"],
        "DELETE": ["assessments.manage"],
    }
    search_fields = ["name", "description"]
    filterset_fields = ["assessment_type", "is_active"]
    ordering = ["name"]
    audit_resource_type = "AssessmentTemplate"

    @action(detail=True, methods=["get", "post"], url_path="questions")
    def questions(self, request, pk=None):
        template = self.get_object()
        if request.method == "GET":
            return Response(
                AssessmentQuestionSerializer(template.questions.all(), many=True).data
            )
        ser = AssessmentQuestionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        q = AssessmentQuestion.objects.create(
            organization=template.organization,
            template=template,
            created_by=request.user,
            updated_by=request.user,
            **ser.validated_data,
        )
        return Response(AssessmentQuestionSerializer(q).data, status=status.HTTP_201_CREATED)


class AssessmentQuestionViewSet(
    OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = AssessmentQuestion.objects.select_related("template")
    serializer_class = AssessmentQuestionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["assessments.view"],
        "POST": ["assessments.manage"],
        "PUT": ["assessments.manage"],
        "PATCH": ["assessments.manage"],
        "DELETE": ["assessments.manage"],
    }
    filterset_fields = ["template", "question_type", "is_knockout"]
    ordering = ["order"]
    audit_resource_type = "AssessmentQuestion"

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        template_id = self.request.data.get("template")
        template = (
            AssessmentTemplate.objects.for_org(self.request.organization)
            .filter(pk=template_id)
            .first()
        )
        if not template:
            raise ValidationError({"template": "Assessment template is required."})
        serializer.save(
            organization=self.request.organization,
            template=template,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class AssessmentAssignmentFilter(filters.FilterSet):
    template = filters.UUIDFilter()
    application = filters.UUIDFilter()
    candidate = filters.UUIDFilter()
    job = filters.UUIDFilter()
    status = filters.CharFilter()
    passed = filters.BooleanFilter()

    class Meta:
        model = AssessmentAssignment
        fields = ["template", "application", "candidate", "job", "status", "passed"]


class AssessmentAssignmentViewSet(
    OrgQuerysetMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = AssessmentAssignment.objects.select_related(
        "template", "application", "candidate", "job"
    ).prefetch_related("answers")
    serializer_class = AssessmentAssignmentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["assessments.view"],
        "POST": ["assessments.create"],
        "PUT": ["assessments.create"],
        "PATCH": ["assessments.create"],
        "DELETE": ["assessments.manage"],
    }
    filterset_class = AssessmentAssignmentFilter
    ordering = ["created_at"]
    audit_resource_type = "AssessmentAssignment"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        action_perms = {
            "assign": ["assessments.create"],
            "submit_answers": ["assessments.create"],
            "score": ["assessments.score"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = AssignAssessmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._assign(request, ser.validated_data)

    def _assign(self, request, data):
        from apps.pipelines.models import Application

        template = (
            AssessmentTemplate.objects.for_org(request.organization)
            .filter(pk=data["template_id"])
            .first()
        )
        application = (
            Application.objects.for_org(request.organization)
            .select_related("candidate", "job")
            .filter(pk=data["application_id"])
            .first()
        )
        if not template or not application:
            return Response(
                {"detail": "Template or application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        assignment = services.assign_assessment(
            organization=request.organization,
            template=template,
            application=application,
            due_at=data.get("due_at"),
            actor=request.user,
            request=request,
        )
        return Response(
            AssessmentAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def assign(self, request):
        ser = AssignAssessmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._assign(request, ser.validated_data)

    @action(detail=True, methods=["post"], url_path="submit-answers")
    def submit_answers(self, request, pk=None):
        assignment = self.get_object()
        ser = SubmitAnswersSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment = services.submit_answers(
            assignment,
            ser.validated_data["answers"],
            actor=request.user,
            auto_score=ser.validated_data.get("auto_score", True),
            request=request,
        )
        return Response(AssessmentAssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        assignment = self.get_object()
        assignment = services.score_assignment(
            assignment, actor=request.user, request=request
        )
        return Response(AssessmentAssignmentSerializer(assignment).data)


class CandidateRatingViewSet(
    OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = CandidateRating.objects.select_related("candidate", "rater", "application")
    serializer_class = CandidateRatingSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["assessments.view"],
        "POST": ["assessments.score"],
        "PUT": ["assessments.score"],
        "PATCH": ["assessments.score"],
        "DELETE": ["assessments.manage"],
    }
    filterset_fields = ["candidate", "application", "rater"]
    ordering = ["-created_at"]
    audit_resource_type = "CandidateRating"

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            rater=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class HiringCommentViewSet(
    OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = HiringComment.objects.select_related("author", "candidate", "parent").prefetch_related(
        "mentions", "replies"
    )
    serializer_class = HiringCommentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["assessments.view", "candidates.view"],
        "POST": ["candidates.edit"],
        "PUT": ["candidates.edit"],
        "PATCH": ["candidates.edit"],
        "DELETE": ["candidates.edit"],
    }
    filterset_fields = ["candidate", "application", "parent", "is_resolved"]
    ordering = ["created_at"]
    audit_resource_type = "HiringComment"

    def get_queryset(self):
        qs = super().get_queryset()
        # Top-level comments by default unless parent filtered
        if "parent" in self.request.query_params:
            qs = qs.filter(parent__isnull=True)
        return qs

    def create(self, request, *args, **kwargs):
        ser = CreateHiringCommentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        from apps.candidates.models import Candidate
        from apps.pipelines.models import Application

        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response({"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND)
        application = None
        if data.get("application_id"):
            application = (
                Application.objects.for_org(request.organization)
                .filter(pk=data["application_id"])
                .first()
            )
        parent = None
        if data.get("parent_id"):
            parent = (
                HiringComment.objects.for_org(request.organization)
                .filter(pk=data["parent_id"])
                .first()
            )
        comment = services.create_hiring_comment(
            organization=request.organization,
            candidate=candidate,
            author=request.user,
            body=data["body"],
            application=application,
            parent=parent,
            request=request,
        )
        return Response(HiringCommentSerializer(comment).data, status=status.HTTP_201_CREATED)
