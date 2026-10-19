"""
Pipeline ViewSets: templates, stages, applications, board, move/bulk actions.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.pipelines.models import (
    Application,
    ApplicationActivity,
    AutomatedTask,
    BulkActionLog,
    PipelineStage,
    PipelineTemplate,
    StageHistory,
)
from apps.pipelines.serializers import (
    ApplicationActivitySerializer,
    ApplicationListSerializer,
    ApplicationSerializer,
    ApplyToJobSerializer,
    AutomatedTaskSerializer,
    BoardApplicationSerializer,
    BulkActionLogSerializer,
    BulkMoveSerializer,
    BulkRejectSerializer,
    BulkTagSerializer,
    MoveApplicationSerializer,
    PipelineStageSerializer,
    PipelineTemplateSerializer,
    StageHistorySerializer,
)
from apps.pipelines import services


class ApplicationFilter(filters.FilterSet):
    job = filters.UUIDFilter()
    candidate = filters.UUIDFilter()
    stage = filters.UUIDFilter()
    status = filters.CharFilter()
    knockout_failed = filters.BooleanFilter()
    tag = filters.CharFilter(method="filter_tag")
    min_score = filters.NumberFilter(field_name="relevance_score", lookup_expr="gte")

    class Meta:
        model = Application
        fields = ["job", "candidate", "stage", "status", "knockout_failed"]

    def filter_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])


class PipelineTemplateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = PipelineTemplate.objects.prefetch_related("stages")
    serializer_class = PipelineTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["pipelines.view"],
        "POST": ["pipelines.edit"],
        "PUT": ["pipelines.edit"],
        "PATCH": ["pipelines.edit"],
        "DELETE": ["pipelines.edit"],
    }
    search_fields = ["name", "description"]
    ordering = ["name"]
    audit_resource_type = "PipelineTemplate"

    @action(detail=False, methods=["post"], url_path="seed-default")
    def seed_default(self, request):
        template = services.seed_default_pipeline(
            request.organization, actor=request.user, force=request.data.get("force", False)
        )
        return Response(PipelineTemplateSerializer(template).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="stages")
    def stages(self, request, pk=None):
        template = self.get_object()
        if request.method == "GET":
            return Response(PipelineStageSerializer(template.stages.all(), many=True).data)
        ser = PipelineStageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        stage = PipelineStage.objects.create(
            organization=template.organization,
            template=template,
            created_by=request.user,
            updated_by=request.user,
            **ser.validated_data,
        )
        return Response(PipelineStageSerializer(stage).data, status=status.HTTP_201_CREATED)


class PipelineStageViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = PipelineStage.objects.select_related("template")
    serializer_class = PipelineStageSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["pipelines.view"],
        "POST": ["pipelines.edit"],
        "PUT": ["pipelines.edit"],
        "PATCH": ["pipelines.edit"],
        "DELETE": ["pipelines.edit"],
    }
    filterset_fields = ["template", "stage_type", "is_terminal"]
    ordering = ["order"]
    audit_resource_type = "PipelineStage"

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        template_id = self.request.data.get("template")
        template = (
            PipelineTemplate.objects.for_org(self.request.organization)
            .filter(pk=template_id)
            .first()
        )
        if not template:
            raise ValidationError({"template": "Pipeline template is required."})
        serializer.save(
            organization=self.request.organization,
            template=template,
            created_by=self.request.user,
            updated_by=self.request.user,
        )


class ApplicationViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = Application.objects.select_related(
        "job", "candidate", "stage"
    ).prefetch_related("stage_history", "activities")
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["pipelines.view"],
        "POST": ["pipelines.edit"],
        "PUT": ["pipelines.edit"],
        "PATCH": ["pipelines.edit"],
        "DELETE": ["pipelines.edit"],
    }
    filterset_class = ApplicationFilter
    search_fields = [
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
        "job__title",
        "tags",
    ]
    ordering_fields = ["applied_at", "relevance_score", "stage_entered_at"]
    ordering = ["-applied_at"]
    audit_resource_type = "Application"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationSerializer

    def get_permissions(self)
        action_perms = {
            "move": ["pipelines.move"],
            "board": ["pipelines.view"],
            "apply": ["pipelines.view"],
            "bulk_move": ["pipelines.move"],
            "bulk_reject": ["pipelines.move"],
            "bulk_tag": ["pipelines.edit"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        # Prefer /apply action; still allow create via apply serializer fields
        ser = ApplyToJobSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._do_apply(request, ser.validated_data)

    def _do_apply(self, request, data):
        from apps.jobs.models import Job
        from apps.candidates.models import Candidate

        job = Job.objects.for_org(request.organization).filter(pk=data["job_id"]).first()
        candidate = (
            Candidate.objects.for_org(request.organization).filter(pk=data["candidate_id"]).first()
        )
        if not job or not candidate:
            return Response(
                {"detail": "Job or candidate not found."}, status=status.HTTP_404_NOT_FOUND
            )
        app = services.apply_to_job(
            organization=request.organization,
            job=job,
            candidate=candidate,
            answers=data.get("answers") or {},
            cover_letter=data.get("cover_letter", ""),
            source=data.get("source", ""),
            actor=request.user,
            request=request,
        )
        return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def apply(self, request):
        ser = ApplyToJobSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._do_apply(request, ser.validated_data)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        application = self.get_object()
        ser = MoveApplicationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        stage = (
            PipelineStage.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["stage_id"])
            .first()
        )
        if not stage:
            return Response({"detail": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)
        app = services.move_application(
            application,
            stage,
            actor=request.user,
            request=request,
            note=ser.validated_data.get("note", ""),
            rejection_reason=ser.validated_data.get("rejection_reason", ""),
        )
        return Response(ApplicationSerializer(app).data)

    @action(detail=False, methods=["get"])
    def board(self, request):
        job_id = request.query_params.get("job")
        if job_id:
            return Response(
                {"detail": "Query param 'job' is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        from apps.jobs.models import Job

        job = Job.objects.for_org(request.organization).filter(pk=job_id).first()
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        board = services.build_board(job, request.organization)
        columns = {}
        for stage_id, apps in board["columns"].items():
            columns[stage_id] = BoardApplicationSerializer(apps, many=True).data
        return Response(
            {
                "job_id": board["job_id"],
                "pipeline_template_id": board["pipeline_template_id"],
                "stages": PipelineStageSerializer(board["stages"], many=True).data,
                "columns": columns,
            }
        )

    @action(detail=False, methods=["post"], url_path="bulk-move")
    def bulk_move(self, request):
        ser = BulkMoveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        stage = (
            PipelineStage.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["stage_id"])
            .first()
        )
        if not stage:
            return Response({"detail": "Stage not found."}, status=status.HTTP_404_NOT_FOUND)
        log = services.bulk_move(
            ser.validated_data["application_ids"],
            stage,
            organization=request.organization,
            actor=request.user,
            request=request,
            note=ser.validated_data.get("note", ""),
        )
        return Response(BulkActionLogSerializer(log).data)

    @action(detail=False, methods=["post"], url_path="bulk-reject")
    def bulk_reject(self, request):
        ser = BulkRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        to_stage = None
        if ser.validated_data.get("stage_id"):
            to_stage = (
                PipelineStage.objects.for_org(request.organization)
                .filter(pk=ser.validated_data["stage_id"])
                .first()
            )
        log = services.bulk_reject(
            ser.validated_data["application_ids"],
            organization=request.organization,
            actor=request.user,
            request=request,
            reason=ser.validated_data.get("reason", ""),
            to_stage=to_stage,
        )
        return Response(BulkActionLogSerializer(log).data)

    @action(detail=False, methods=["post"], url_path="bulk-tag")
    def bulk_tag(self, request):
        ser = BulkTagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        log = services.bulk_tag(
            ser.validated_data["application_ids"],
            ser.validated_data["tags"],
            organization=request.organization,
            actor=request.user,
            request=request,
            mode=ser.validated_data.get("mode", "add"),
        )
        return Response(BulkActionLogSerializer(log).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        application = self.get_object()
        qs = application.stage_history.select_related("from_stage", "to_stage", "moved_by")
        return Response(StageHistorySerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        application = self.get_object()
        qs = application.activities.select_related("actor")
        return Response(ApplicationActivitySerializer(qs, many=True).data)


class BulkActionLogViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = BulkActionLog.objects.all()
    serializer_class = BulkActionLogSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["pipelines.view"]}
    filterset_fields = ["action_type"]
    ordering = ["-created_at"]


class AutomatedTaskViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AutomatedTask.objects.select_related("application", "stage")
    serializer_class = AutomatedTaskSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["pipelines.view"]}
    filterset_fields = ["application", "status", "task"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        task = self.get_object()
        task.status = AutomatedTask.Status.PENDING
        task.error = ""
        task.save(update_fields=["status", "error", "updated_at"])
        from apps.pipelines.tasks import run_stage_automations

        run_stage_automations.delay(str(task.application_id), str(task.stage_id) if task.stage_id else None)
        return Response(AutomatedTaskSerializer(task).data)
