"""
Celery tasks for automation: async evaluation, date-based queue, cleanup.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def evaluate_rule_for_event(
    self,
    rule_id: str,
    trigger_event: str,
    entity_type: str = "",
    entity_id: str = "",
):
    """Async entry point for rule evaluation."""
    from apps.automation.models import AutomationRule
    from apps.automation.services import evaluate_rule_for_event as evaluate

    try:
        rule = AutomationRule.objects.select_related("organization").get(pk=rule_id)
    except AutomationRule.DoesNotExist:
        logger.warning("evaluate_rule_for_event: rule %s not found", rule_id)
        return {"ok": False, "error": "rule_not_found"}

    try:
        result = evaluate(rule, trigger_event, entity_type=entity_type, entity_id=entity_id)
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        logger.exception("evaluate_rule_for_event failed for rule %s", rule_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_pending_actions(self, limit: int = 500):
    """Drain date-based rules whose offset has elapsed for matching entities."""
    from django.apps import apps as django_apps

    from apps.automation.models import AutomationRule, RuleExecution
    from apps.automation.services import ENTITY_REGISTRY, evaluate_rule_for_event

    now = timezone.now()
    processed = 0
    rules = AutomationRule.objects.filter(
        trigger=AutomationRule.Trigger.DATE_BASED,
        is_active=True,
        is_deleted=False,
    ).select_related("organization")

    for rule in rules.iterator():
        config = rule.trigger_config or {}
        entity_type = config.get("entity_type", "")
        date_field = config.get("date_field", "")
        offset_days = int(config.get("offset_days", 0))
        if not entity_type or not date_field:
            continue
        entry = ENTITY_REGISTRY.get(entity_type)
        if not entry:
            continue
        app_label, model_name = entry
        try:
            model = django_apps.get_model(app_label, model_name)
        except LookupError:
            continue
        if not hasattr(model, date_field) or not hasattr(model, "organization_id"):
            continue

        cutoff = now + timezone.timedelta(days=offset_days)
        already_run = set(
            RuleExecution.objects.filter(
                rule=rule,
                trigger_event=AutomationRule.Trigger.DATE_BASED,
                entity_type=entity_type,
            ).values_list("entity_id", flat=True)
        )
        qs = (
            model.objects.filter(organization=rule.organization, **{f"{date_field}__lte": cutoff})
            .exclude(pk__in=already_run)
            .order_by(date_field)[:limit]
        )
        for entity in qs.iterator():
            evaluate_rule_for_event(
                rule,
                AutomationRule.Trigger.DATE_BASED,
                entity_type=entity_type,
                entity_id=str(entity.pk),
                entity=entity,
            )
            processed += 1
    return {"ok": True, "processed": processed}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def cleanup_old_executions(self, retention_days: int = 90):
    """Hard-delete executions and action logs older than retention_days."""
    from apps.automation.models import RuleActionLog, RuleExecution

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    old_executions = RuleExecution.all_objects.filter(created_at__gt=cutoff)
    action_logs_deleted, _ = RuleActionLog.all_objects.filter(
        execution__in=old_executions.values("pk")
    ).delete()
    executions_deleted, _ = old_executions.delete()
    return {
        "ok": True,
        "deleted_executions": executions_deleted,
        "deleted_action_logs": action_logs_deleted,
    }
