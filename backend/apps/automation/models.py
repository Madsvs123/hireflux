"""
Workflow automation: rules, executions, and per-action logs.
"""
from django.db import models
from django.utils import timezone

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class AutomationRule(TenantModel, SoftDeleteModel, AuditedModel):
    """A rule that fires on a trigger when conditions match."""

    class Trigger(models.TextChoices):
        STAGE_CHANGE = "stage_change", "Stage Change"
        JOB_PUBLISHED = "job_published", "Job Published"
        CANDIDATE_CREATED = "candidate_created", "Candidate Created"
        OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
        ASSESSMENT_COMPLETED = "assessment_completed", "Assessment Completed"
        DATE_BASED = "date_based", "Date Based"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    trigger = models.CharField(
        max_length=32,
        choices=Trigger.choices,
        db_index=True,
    )
    trigger_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Trigger-specific config e.g. {stage_id, job_id, days, entity_type}.",
    )
    conditions = models.JSONField(
        default=list,
        blank=True,
        help_text="AND/OR expression: {operator: 'and'|'or', rules: [{field, operator, value}]}.",
    )
    actions = models.JSONField(
        default=list,
        blank=True,
        help_text="[{type: send_email|notify|create_task|move_stage|update_field|send_webhook, params}].",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    run_count = models.PositiveIntegerField(default=0)
    last_run_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "trigger", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.trigger})"


class RuleExecution(TenantModel, SoftDeleteModel, AuditedModel):
    """One evaluation of a rule against a trigger event."""

    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name="executions",
    )
    trigger_event = models.CharField(max_length=32, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, default="")
    entity_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        db_index=True,
    )
    conditions_evaluated = models.JSONField(default=dict, blank=True)
    executed_at = models.DateTimeField(default=timezone.now, db_index=True)
    error = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-executed_at"]
        indexes = [
            models.Index(fields=["rule", "status"]),
            models.Index(fields=["rule", "trigger_event", "entity_id"]),
        ]

    def __str__(self):
        return f"RuleExec {self.rule_id} [{self.status}]"


class RuleActionLog(TenantModel, SoftDeleteModel, AuditedModel):
    """Per-action outcome inside a rule execution."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    execution = models.ForeignKey(
        RuleExecution,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    action_index = models.PositiveIntegerField(default=0)
    action_type = models.CharField(max_length=32)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        db_index=True,
    )
    detail = models.JSONField(default=dict, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["execution", "action_index"]
        indexes = [
            models.Index(fields=["execution", "status"]),
        ]

    def __str__(self):
        return f"#{self.action_index} {self.action_type} [{self.status}]"
