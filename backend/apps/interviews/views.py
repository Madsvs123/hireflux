"""
Interview ViewSets: kits, panels, interviews, calendar, scorecards, decisions.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.interviews import services
from apps.interviews.models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAvailability,
    InterviewKit,
    InterviewPanel,
    Scorecard,
)
from apps.interviews.serializers import (
    AvailabilitySlotsSerializer,
    CancelInterviewSerializer,
    DecisionSerializer,
    InterviewDecisionSummarySerializer,
    InterviewerAvailabilitySerializer,
    InterviewKitSerializer,
    InterviewListSerializer,
    InterviewPanelSerializer,
    InterviewSerializer,
    ScheduleInterviewSerializer,
    ScorecardSerializer,
    SubmitScorecardSerializer,
)


class InterviewFilter(filters.FilterSet):
    application = filters.UUIDFilter()
    job = filters.UUIDFilter()
    candidate = filters.UUIDFilter()
    status = filters.CharFilter()
    interview_type = filters.CharFilter()
    start = filters.IsoDateTimeFilter(field_name="scheduled_start", lookup_expr="gte")
    end = filters.IsoDateTimeFilter(field_name="scheduled_end", lookup_expr="gte")

    class Meta:
        model = Interview
        fields = ["application", "job", "candidate", "status", "interview_type"]


class InterviewKitViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = InterviewKit.objects.all()
    serializer_class = InterviewKitSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["interviews.view"],
        "POST": ["interviews.manage"],
        "PUT": ["interviews.manage"],
        "PATCH": ["interviews.manage"],
        "DELETE": ["interviews.manage"],
    }
    search_fields = ["name", "description"]
    ordering = ["name"]
    audit_resource_type = "InterviewKit"


class InterviewPanelViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = InterviewPanel.objects.prefetch_related("members")
    serializer_class = InterviewPanelSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["interviews.view"],
        "POST": ["interviews.manage"],
        "PUT": ["interviews.manage"],
        "PATCH": ["interviews.manage"],
        "DELETE": ["interviews.view"],
    }
    search_fields = ["name"]
    ordering = ["name"]
    audit_resource_type = "InterviewPanel"


class InterviewerAvailabilityViewSet(
    OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = InterviewerAvailability.objects.select_related("interviewer")
    serializer_class = InterviewerAvailabilitySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["interviews.view"],
        "POST": ["interviews.schedule"],
        "PUT": ["interviews.schedule"],
        "PATCH": ["interviews.schedule"],
        "DELETE": ["interviews.schedule"],
    }
    filterset_fields = ["interviewer"]
    ordering = ["start"]
    audit_resource_type = "InterviewerAvailability"

    @action(detail=False, methods=["post"], url_path="find-slots")
    def find_slots(self, request):
        ser = AvailabilitySlotsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        slots = services.find_availability_slots(
            organization=request.organization,
            interviewer_ids=data["interviewer_ids"],
            duration_minutes=data.get("duration_minutes", 60),
            window_start=data.get("window_start"),
            window_end=data.get("window_end"),
            slot_step_minutes=data.get("slot_step_minutes", 30),
        )
        return Response({"slots": slots})


class InterviewViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = Interview.objects.select_related(
        "application", "job", "candidate", "kit", "panel"
    ).prefetch_related("assignments__interviewer", "scorecards")
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["interviews.view"],
        "POST": ["interviews.schedule"],
        "PUT": ["interviews.schedule"],
        "PATCH": ["interviews.schedule"],
        "DELETE": ["interviews.schedule"],
    }
    filterset_class = InterviewFilter
    search_fields = ["title", "candidate__first_name", "candidate__last_name", "job__title"]
    ordering = ["scheduled_start"]
    audit_resource_type = "Interview"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self)
        if self.action == "list":
            return InterviewListSerializer
        return InterviewSerializer

    def get_permissions(self):
        action_perms = {
            "schedule": ["interviews.schedule"],
            "cancel": ["interviews.schedule"],
            "submit_scorecard": ["interviews.view"],
            "decision": ["interviews.manage"],
            "calendar": ["interviews.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = ScheduleInterviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._schedule(request, ser.validated_data)

    def _schedule(self, request, data):
        from apps.pipelines.models import Application

        application = (
            Application.objects.for_org(request.organization)
            .select_related("job", "candidate")
            .filter(pk=data["application_id"])
            .first()
        )
        if not application:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        kit = None
        panel = None
        if data.get("kit_id"):
            kit = InterviewKit.objects.for_org(request.organization).filter(pk=data["kit_id"]).first()
        if data.get("panel_id"):
            panel = (
                InterviewPanel.objects.for_org(request.organization)
                .filter(pk=data["panel_id"])
                .first()
            )

        interview = services.schedule_interview(
            organization=request.organization,
            application=application,
            scheduled_start=data["scheduled_start"],
            scheduled_end=data["scheduled_end"],
            interviewer_ids=data.get("interviewer_ids") or [],
            kit=kit,
            panel=panel,
            interview_type=data.get("interview_type", Interview.InterviewType.VIDEO),
            title=data.get("title", ""),
            location=data.get("location", ""),
            meeting_url=data.get("meeting_url", ""),
            timezone_name=data.get("timezone", "UTC"),
            notes=data.get("notes", ""),
            actor=request.user,
            request=request,
        )
        return Response(InterviewSerializer(interview).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def schedule(self, request):
        ser = ScheduleInterviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._schedule(request, ser.validated_data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        interview = self.get_object()
        ser = CancelInterviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        interview = services.cancel_interview(
            interview,
            reason=ser.validated_data.get("reason", ""),
            actor=request.user,
            request=request,
        )
        return Response(InterviewSerializer(interview).data)

    @action(detail=True, methods=["post"], url_path="submit-scorecard")
    def submit_scorecard(self, request, pk=None):
        interview = self.get_object()
        ser = SubmitScorecardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        scorecard = services.submit_scorecard(
            interview,
            request.user,
            scores=ser.validated_data.get("scores") or {},
            recommendation=ser.validated_data.get(
                "recommendation", Scorecard.Recommendation.NEUTRAL
            ),
            strengths=ser.validated_data.get("strengths", ""),
            concerns=ser.validated_data.get("concerns", ""),
            private_notes=ser.validated_data.get("private_notes", ""),
            actor=request.user,
            request=request,
        )
        return Response(ScorecardSerializer(scorecard).data)

    @action(detail=True, methods=["get", "post"])
    def decision(self, request, pk=None):
        interview = self.get_object()
        if request.method == "GET":
            summary = getattr(interview, "decision_summary", None)
            if summary is None:
                summary = services.compute_decision_summary(interview, actor=request.user)
            return Response(InterviewDecisionSummarySerializer(summary).data)

        ser = DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        summary = services.compute_decision_summary(
            interview,
            actor=request.user,
            request=request,
            decision=ser.validated_data["decision"],
        )
        return Response(InterviewDecisionSummarySerializer(summary).data)

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """Date-range calendar feed: ?start=&end="""
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if not start or not end:
            return Response(
                {"detail": "Query params 'start' and 'end' (ISO datetime) are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = (
            self.get_queryset()
            .filter(scheduled_end__gte=start, scheduled_start__lte=end)
            .filter(status=Interview.Status.CANCELLED)
        )
        return Response(InterviewListSerializer(qs, many=True).data)


class ScorecardViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Scorecard.objects.select_related("interview", "interviewer")
    serializer_class = ScorecardSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["interviews.view"]}
    filterset_fields = ["interview", "interviewer", "is_submitted", "recommendation"]
    ordering = ["-submitted_at", "-created_at"]


class InterviewDecisionSummaryViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = InterviewDecisionSummary.objects.select_related("interview", "application")
    serializer_class = InterviewDecisionSummarySerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["interviews.view"]}
    filterset_fields = ["interview", "application", "decision"]
    ordering = ["-created_at"]
