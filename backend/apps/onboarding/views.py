"""
Onboarding ViewSets: templates, plans, plan tasks, documents.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.mixins import (
    AuditMixin,
    OrgCreateMixin,
    OrgQuerysetMixin,
    SoftDeleteDestroyMixin,
)
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.onboarding import services
from apps.onboarding.models import (
    OnboardingDocument,
    OnboardingPlan,
    OnboardingPlanTask,
    OnboardingTaskDefinition,
    OnboardingTemplate,
)
from apps.onboarding.serializers import (
    BlockTaskSerializer,
    CreateOnboardingDocumentSerializer,
    CreatePlanSerializer,
    CreateTaskSerializer,
    OnboardingDocumentSerializer,
    OnboardingPlanSerializer,
    OnboardingPlanTaskSerializer,
    OnboardingTaskDefinitionSerializer,
    OnboardingTemplateSerializer,
)

ONBOARDING_PERMISSION_MAP = {
    "SAFE": ["onboarding.view"],
    "POST": ["onboarding.view"],
    "PUT": ["onboarding.manage"],
    "PATCH": ["onboarding.manage"],
    "DELETE": ["onboarding.manage"],
}


class OnboardingTemplateViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = OnboardingTemplate.objects.prefetch_related("task_definitions")
    serializer_class = OnboardingTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = ONBOARDING_PERMISSION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["is_active"]
    ordering = ["name"]
    audit_resource_type = "OnboardingTemplate"

    def get_permissions(self):
        if self.action == "duplicate":
            self.required_permissions = ["onboarding.manage"]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a template with all of its task definitions."""
        template = self.get_object()
        copy = services.duplicate_template(template, actor=request.user)
        return Response(
            OnboardingTemplateSerializer(copy).data,
            status=status.HTTP_201_CREATED,
        )


class OnboardingTaskDefinitionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = OnboardingTaskDefinition.objects.select_related("template")
    serializer_class = OnboardingTaskDefinitionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = ONBOARDING_PERMISSION_MAP
    search_fields = ["title", "description", "owner_role"]
    filterset_fields = ["template", "required"]
    ordering = ["order", "created_at"]
    audit_resource_type = "OnboardingTaskDefinition"


class OnboardingPlanFilter(filters.FilterSet):
    candidate = filters.UUIDFilter()
    offer = filters.UUIDFilter()
    template = filters.UUIDFilter()
    status = filters.CharFilter()

    class Meta:
        model = OnboardingPlan
        fields = ["candidate", "offer", "template", "status"]


class OnboardingPlanViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = OnboardingPlan.objects.select_related("candidate", "offer", "template")
    serializer_class = OnboardingPlanSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = ONBOARDING_PERMISSION_MAP
    filterset_class = OnboardingPlanFilter
    search_fields = [
        "candidate__first_name",
        "candidate__last_name",
        "candidate__email",
    ]
    ordering = ["-created_at"]
    audit_resource_type = "OnboardingPlan"

    def get_permissions(self):
        action_perms = {
            "start": ["onboarding.manage"],
            "cancel": ["onboarding.manage"],
            "send_reminders": ["onboarding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreatePlanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        from apps.candidates.models import Candidate
        from apps.offers.models import Offer

        candidate = (
            Candidate.objects.for_org(request.organization)
            .filter(pk=data["candidate_id"])
            .first()
        )
        if not candidate:
            return Response(
                {"detail": "Candidate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        offer = None
        if data.get("offer_id"):
            offer = (
                Offer.objects.for_org(request.organization)
                .filter(pk=data["offer_id"])
                .first()
            )
            if not offer:
                return Response(
                    {"detail": "Offer not found."}, status=status.HTTP_404_NOT_FOUND
                )

        template = None
        if data.get("template_id"):
            template = (
                OnboardingTemplate.objects.for_org(request.organization)
                .filter(pk=data["template_id"])
                .first()
            )
            if not template:
                return Response(
                    {"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND
                )

        plan = services.create_plan(
            request.organization,
            candidate=candidate,
            offer=offer,
            template=template,
            start_date=data.get("start_date"),
            actor=request.user,
        )
        return Response(
            OnboardingPlanSerializer(plan).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Activate the plan and instantiate tasks from its template."""
        plan = self.get_object()
        template = plan.template
        template_id = request.data.get("template_id")
        if template_id:
            template = (
                OnboardingTemplate.objects.for_org(request.organization)
                .filter(pk=template_id)
                .first()
            )
            if not template:
                return Response(
                    {"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND
                )
        plan = services.start_plan(plan, template=template, actor=request.user)
        return Response(OnboardingPlanSerializer(plan).data)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        """Task/document status counts for the plan."""
        plan = self.get_object()
        return Response(services.plan_progress(plan))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        plan = self.get_object()
        plan = services.cancel_plan(plan, actor=request.user)
        return Response(OnboardingPlanSerializer(plan).data)

    @action(detail=True, methods=["post"], url_path="send-reminders")
    def send_reminders(self, request, pk=None):
        """Queue reminder notifications for this plan's due/overdue tasks."""
        plan = self.get_object()
        from apps.onboarding.tasks import send_onboarding_reminders

        send_onboarding_reminders.delay(str(plan.pk))
        return Response(
            {"queued": True, "plan_id": str(plan.pk)},
            status=status.HTTP_202_ACCEPTED,
        )


class OnboardingPlanTaskViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = OnboardingPlanTask.objects.select_related(
        "plan", "definition", "completed_by"
    )
    serializer_class = OnboardingPlanTaskSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = ONBOARDING_PERMISSION_MAP
    search_fields = ["title", "notes"]
    filterset_fields = ["plan", "definition", "status"]
    ordering = ["due_date", "created_at"]
    audit_resource_type = "OnboardingPlanTask"

    def get_permissions(self):
        action_perms = {
            "complete": ["onboarding.manage"],
            "reopen": ["onboarding.manage"],
            "block": ["onboarding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateTaskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        plan = (
            OnboardingPlan.objects.for_org(request.organization)
            .filter(pk=data["plan_id"])
            .first()
        )
        if not plan:
            return Response(
                {"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND
            )

        definition = None
        if data.get("definition_id"):
            definition = (
                OnboardingTaskDefinition.objects.for_org(request.organization)
                .filter(pk=data["definition_id"])
                .first()
            )
            if not definition:
                return Response(
                    {"detail": "Definition not found."}, status=status.HTTP_404_NOT_FOUND
                )

        task = services.create_task(
            plan,
            definition=definition,
            title=data.get("title", ""),
            due_date=data.get("due_date"),
            actor=request.user,
        )
        return Response(
            OnboardingPlanTaskSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        task = services.complete_task(task, actor=request.user)
        return Response(OnboardingPlanTaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        task = self.get_object()
        task = services.reopen_task(task, actor=request.user)
        return Response(OnboardingPlanTaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        task = self.get_object()
        ser = BlockTaskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        task = services.block_task(
            task,
            note=ser.validated_data.get("note", ""),
            actor=request.user,
        )
        return Response(OnboardingPlanTaskSerializer(task).data)


class OnboardingDocumentViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = OnboardingDocument.objects.select_related(
        "plan", "uploaded_by", "approved_by"
    )
    serializer_class = OnboardingDocumentSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = ONBOARDING_PERMISSION_MAP
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["plan", "status"]
    search_fields = ["name"]
    ordering = ["-created_at"]
    audit_resource_type = "OnboardingDocument"

    def get_permissions(self):
        action_perms = {
            "approve": ["onboarding.manage"],
            "reject": ["onboarding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateOnboardingDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        plan = (
            OnboardingPlan.objects.for_org(request.organization)
            .filter(pk=data["plan_id"])
            .first()
        )
        if not plan:
            return Response(
                {"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND
            )

        document = services.upload_document(
            plan,
            name=data["name"],
            file=data.get("file"),
            actor=request.user,
        )
        return Response(
            OnboardingDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        if "file" in serializer.validated_data and instance.file:
            instance.status = OnboardingDocument.Status.UPLOADED
            instance.uploaded_by = self.request.user
            instance.save(update_fields=["status", "uploaded_by", "updated_at"])

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        document = self.get_object()
        document = services.approve_document(document, actor=request.user)
        return Response(OnboardingDocumentSerializer(document).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        document = self.get_object()
        document = services.reject_document(document, actor=request.user)
        return Response(OnboardingDocumentSerializer(document).data)
