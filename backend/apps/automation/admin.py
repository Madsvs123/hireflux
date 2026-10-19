"""
Django admin for automation domain.
"""
from django.contrib import admin

from apps.automation.models import AutomationRule, RuleActionLog, RuleExecution


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "trigger", "is_active", "run_count", "last_run_at")
    list_filter = ("trigger", "is_active")
    search_fields = ("name", "description")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("run_count", "last_run_at", "created_at", "updated_at")


@admin.register(RuleExecution)
class RuleExecutionAdmin(admin.ModelAdmin):
    list_display = ("rule", "trigger_event", "entity_type", "entity_id", "status", "executed_at")
    list_filter = ("status", "trigger_event")
    search_fields = ("entity_id", "error")
    raw_id_fields = ("organization", "rule", "created_by", "updated_by")
    readonly_fields = ("conditions_evaluated", "executed_at", "created_at", "updated_at")


@admin.register(RuleActionLog)
class RuleActionLogAdmin(admin.ModelAdmin):
    list_display = ("execution", "action_index", "action_type", "status", "executed_at")
    list_filter = ("status", "action_type")
    search_fields = ("action_type",)
    raw_id_fields = ("organization", "execution", "created_by", "updated_by")
    readonly_fields = ("detail", "executed_at", "created_at", "updated_at")
