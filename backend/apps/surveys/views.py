"""
Surveys ViewSets: templates, questions, instances, responses, analytics, public submit.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.surveys import services
from apps.surveys.models import (
    SurveyInstance,
    SurveyInvitation,
    SurveyQuestion,
    SurveyResponse,
    SurveyTemplate,
)
from apps.surveys.serializers import (
    PublicSurveySubmitSerializer,
    SurveyAnalyticsSerializer,
    SurveyInstanceSerializer,
    SurveyInvitationSerializer,
    SurveyQuestionSerializer,
    SurveyResponseSerializer,
    SurveyTemplateSerializer,
)


class SurveyTemplateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SurveyTemplate.objects.prefetch_related("questions")
    serializer_class = SurveyTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["surveys.view"],
        "POST": ["surveys.manage"],
        "PUT": ["surveys.manage"],
        "PATCH": ["surveys.manage"],
        "DELETE": ["surveys.manage"],
    }
    filterset_fields = ["survey_type", "is_active"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    audit_resource_type = "SurveyTemplate"

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        template = self.get_object()
        copy = services.duplicate_template(template, actor=request.user)
        return Response(
            SurveyTemplateSerializer(copy).data,
            status=status.HTTP_201_CREATED,
        )


class SurveyQuestionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SurveyQuestion.objects.select_related("template")
    serializer_class = SurveyQuestionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["surveys.view"],
        "POST": ["surveys.manage"],
        "PUT": ["surveys.manage"],
        "PATCH": ["surveys.manage"],
        "DELETE": ["surveys.manage"],
    }
    filterset_fields = ["template", "question_type", "is_required"]
    search_fields = ["question_text"]
    ordering = ["template", "order"]
    audit_resource_type = "SurveyQuestion"


class SurveyInstanceViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SurveyInstance.objects.select_related(
        "template", "candidate", "job"
    ).prefetch_related("responses", "invitations")
    serializer_class = SurveyInstanceSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["surveys.view"],
        "POST": ["surveys.manage"],
        "PUT": ["surveys.manage"],
        "PATCH": ["surveys.manage"],
        "DELETE": ["surveys.manage"],
    }
    filterset_fields = ["template", "candidate", "job", "status", "anonymous"]
    search_fields = ["template__name", "candidate__email"]
    ordering = ["-created_at"]
    audit_resource_type = "SurveyInstance"

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        instance = self.get_object()
        instance = services.send_instance(instance, actor=request.user)
        return Response(SurveyInstanceSerializer(instance).data)

    @action(detail=True, methods=["post"], url_path="send-reminder")
    def send_reminder(self, request, pk=None):
        instance = self.get_object()
        instance = services.send_reminder(instance, actor=request.user)
        return Response(SurveyInstanceSerializer(instance).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        instance = self.get_object()
        instance = services.close_instance(instance, actor=request.user)
        return Response(SurveyInstanceSerializer(instance).data)


class SurveyResponseViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SurveyResponse.objects.select_related("instance", "question")
    serializer_class = SurveyResponseSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["surveys.view"]}
    filterset_fields = ["instance", "question"]
    ordering = ["-answered_at"]

    def get_permissions(self):
        if self.action == "submit":
            self.required_permissions = ["surveys.manage"]
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def submit(self, request):
        """Staff-side submission of a response on behalf of a candidate."""
        ser = PublicSurveySubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        instance_id = data.get("instance_id")
        if not instance_id:
            return Response(
                {"instance_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance = (
            SurveyInstance.objects.for_org(request.organization)
            .filter(pk=instance_id)
            .first()
        )
        if not instance:
            return Response(
                {"detail": "Instance not found."}, status=status.HTTP_404_NOT_FOUND
            )
        question = (
            SurveyQuestion.objects.for_org(request.organization)
            .filter(pk=data["question_id"], template=instance.template)
            .first()
        )
        if not question:
            return Response(
                {"detail": "Question not found for this survey."},
                status=status.HTTP_404_NOT_FOUND,
            )
        response = services.submit_response(instance, question, data["answer"])
        return Response(SurveyResponseSerializer(response).data)


class SurveyInvitationViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SurveyInvitation.objects.select_related("instance")
    serializer_class = SurveyInvitationSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["surveys.view"],
        "POST": ["surveys.manage"],
        "PUT": ["surveys.manage"],
        "PATCH": ["surveys.manage"],
        "DELETE": ["surveys.manage"],
    }
    filterset_fields = ["instance", "email", "status"]
    search_fields = ["email"]
    ordering = ["-created_at"]
    audit_resource_type = "SurveyInvitation"


class SurveyAnalyticsView(APIView):
    """Aggregate analytics for a survey template."""

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["surveys.view"]

    def get(self, request):
        ser = SurveyAnalyticsSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        template = (
            SurveyTemplate.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["template_id"])
            .first()
        )
        if not template:
            return Response(
                {"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(services.survey_analytics(template))


# ---------------------------------------------------------------------------
# Public (anonymous) survey endpoints
# ---------------------------------------------------------------------------


class PublicSurveyDetailView(APIView):
    """Anonymous survey detail: questions + status, no PII."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            instance = services.get_instance_by_token(token)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_404_NOT_FOUND)
        return Response(services.public_survey_payload(instance))


class PublicSurveySubmitView(APIView):
    """Anonymous single-answer submission keyed by instance token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, token):
        try:
            instance = services.get_instance_by_token(token)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_404_NOT_FOUND)
        ser = PublicSurveySubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        question = (
            SurveyQuestion.objects.filter(
                template=instance.template,
                pk=ser.validated_data["question_id"],
                is_deleted=False,
            )
            .filter(organization=instance.organization)
            .first()
        )
        if not question:
            return Response(
                {"detail": "Question not found for this survey."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            response = services.submit_response(
                instance, question, ser.validated_data["answer"]
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "ok": True,
                "response_id": str(response.pk),
                "instance_status": instance.status,
            }
        )
