"""
Automation ViewSets: rules, executions, action logs, and the debug trigger endpoint.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automation.models import AutomationRule, RuleActionLog, RuleExecution
from apps.automation.serializers import (
    AutomationEventSerializer,
    AutomationRuleSerializer,
    RuleActionLogSerializer,
    RuleExecutionSerializer,
    TestRunSerializer,
)
from apps.automation import services
from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class AutomationRuleViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = AutomationRule.objects.select_related("organization")
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["automation.view"],
        "POST": ["automation.manage"],
        "PUT": ["automation.manage"],
        "PATCH": ["automation.manage"],
        "DELETE": ["automation.manage"],
    }
    filterset_fields = ["trigger", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name", "trigger", "run_count", "last_run_at"]
    ordering = ["-created_at"]
    audit_resource_type = "AutomationRule"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "enable": ["automation.manage"],
            "disable": ["automation.manage"],
            "test_run": ["automation.view"],
            "duplicate": ["automation.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def enable(self, request, pk=None):
        rule = self.get_object()
        rule.is_active = True
        rule.updated_by = request.user
        rule.save()
        return Response(AutomationRuleSerializer(rule).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        rule = self.get_object()
        rule.is_active = False
        rule.updated_by = request.user
        rule.save()
        return Response(AutomationRuleSerializer(rule).data)

    @action(detail=True, methods=["post"], url_path="test-run")
    def test_run(self, request, pk=None):
        rule = self.get_object()
        ser = TestRunSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan = services.test_run(
            rule,
            entity_type=ser.validated_data.get("entity_type", ""),
            entity_id=ser.validated_data.get("entity_id", ""),
        )
        return Response(plan)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        rule = self.get_object()
        clone = services.duplicate_rule(rule, actor=request.user)
        return Response(AutomationRuleSerializer(clone).data, status=status.HTTP_201_CREATED)


class RuleExecutionViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = RuleExecution.objects.select_related("rule", "organization")
    serializer_class = RuleExecutionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["automation.view"]}
    filterset_fields = ["rule", "status", "trigger_event", "entity_type", "entity_id"]
    search_fields = ["error"]
    ordering_fields = ["executed_at", "created_at", "status"]
    ordering = ["-executed_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "retry": ["automation.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        execution = self.get_object()
        if execution.status == RuleExecution.Status.FAILED:
            return Response(
                {"detail": "Only failed executions can be retried."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = services.evaluate_rule_for_event(
            execution.rule,
            execution.trigger_event,
            entity_type=execution.entity_type,
            entity_id=execution.entity_id,
            actor=request.user,
        )
        return Response(result)


class RuleActionLogViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = RuleActionLog.objects.select_related("execution", "organization")
    serializer_class = RuleActionLogSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["automation.view"]}
    filterset_fields = ["execution", "status", "action_type"]
    ordering_fields = ["executed_at", "action_index", "created_at", "status"]
    ordering = ["execution", "action_index"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs


class AutomationEventView(APIView):
    """
    Debug endpoint to fire a trigger event manually.

    GET lists supported triggers; POST evaluates all matching active rules
    (sync or async) and returns the resulting executions.
    """

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "GET": ["automation.view"],
        "POST": ["automation.manage"],
    }

    def get(self, request):
        return Response(
            {
                "triggers": [choice[0] for choice in AutomationRule.Trigger.choices],
                "actions": sorted(services.SUPPORTED_ACTIONS),
                "entity_types": sorted(services.ENTITY_REGISTRY.keys()),
            }
        )

    def post(self, request):
        ser = AutomationEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        result = services.fire_trigger(
            organization=request.organization,
            trigger_event=data["trigger_event"],
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            actor=request.user,
            async_mode=data.get("async_mode", False),
        )
        return Response(result)
