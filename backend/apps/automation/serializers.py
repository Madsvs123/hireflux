"""
Serializers for automation domain.
"""
from rest_framework import serializers

from apps.automation.models import AutomationRule, RuleActionLog, RuleExecution

SUPPORTED_ACTION_TYPES = {
    "send_email",
    "notify",
    "create_task",
    "move_stage",
    "update_field",
}


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "name",
            "description",
            "trigger",
            "trigger_config",
            "conditions",
            "actions",
            "is_active",
            "run_count",
            "last_run_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "run_count",
            "last_run_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate_actions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Actions must be a list.")
        for index, action in enumerate(value):
            if not isinstance(action, dict) or not action.get("type"):
                raise serializers.ValidationError(
                    f"Action at index {index} must be an object with a 'type'."
                )
            if action["type"] not in SUPPORTED_ACTION_TYPES:
                raise serializers.ValidationError(
                    f"Unsupported action type '{action['type']}' at index {index}."
                )
            if "params" in action and not isinstance(action["params"], dict):
                raise serializers.ValidationError(
                    f"Action at index {index} params must be an object."
                )
        return value

    def validate_conditions(self, value):
        if value is None:
            return []
        if not isinstance(value, list) and not isinstance(value, dict):
            raise serializers.ValidationError("Conditions must be a list or an AND/OR object.")
        return value


class RuleExecutionSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)

    class Meta:
        model = RuleExecution
        fields = [
            "id",
            "rule",
            "rule_name",
            "trigger_event",
            "entity_type",
            "entity_id",
            "status",
            "conditions_evaluated",
            "executed_at",
            "error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RuleActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleActionLog
        fields = [
            "id",
            "execution",
            "action_index",
            "action_type",
            "status",
            "detail",
            "executed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TestRunSerializer(serializers.Serializer):
    entity_type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    entity_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class AutomationEventSerializer(serializers.Serializer):
    trigger_event = serializers.ChoiceField(choices=AutomationRule.Trigger.choices)
    entity_type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    entity_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    async_mode = serializers.BooleanField(required=False, default=False)
