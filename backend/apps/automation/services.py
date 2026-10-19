"""
Automation rule engine: condition evaluation and action execution.

Conditions are an AND/OR expression tree:
    {"operator": "and", "rules": [{"field": "candidate.email", "operator": "contains", "value": "@"}, ...]}

Actions are a list of {"type": ..., "params": {...}} executed in order, each
logged on a RuleActionLog row.
"""
from __future__ import annotations

import copy
import json
import logging
import urllib.request

from django.apps import apps
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.automation.models import AutomationRule, RuleActionLog, RuleExecution

logger = logging.getLogger(__name__)

SUPPORTED_ACTIONS = {"send_email", "notify", "create_task", "move_stage", "update_field", "send_webhook"}
CONDITION_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "contains", "in", "not_in"}

# Entity types that rules can reference in conditions/actions.
ENTITY_REGISTRY = {
    "application": ("pipelines", "Application"),
    "candidate": ("candidates", "Candidate"),
    "job": ("jobs", "Job"),
    "offer": ("offers", "Offer"),
    "stage": ("pipelines", "PipelineStage"),
    "interview": ("interviews", "Interview"),
    "assessment": ("assessments", "AssessmentAssignment"),
}


def _json_safe(value):
    """Best-effort JSON-safe conversion (UUIDs, datetimes, decimals)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _compare(left, operator: str, right) -> bool
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left is not None and right is not None and left > right
    if operator == "gte":
        return left is not None and right is not None and left >= right
    if operator == "lt":
        return left is not None and right is not None and left <= right
    if operator == "lte":
        return left is not None and right is not None and left < right
    if operator == "contains":
        if left is None:
            return False
        return right in left if isinstance(left, (str, list, dict)) else False
    if operator == "in":
        return left in (right or [])
    if operator == "not_in":
        return left not in (right or [])
    return False


def _resolve_field(data, field):
    """Resolve a dotted path (e.g. 'candidate.email') against a data dict."""
    if not field:
        return None
    current = data
    for part in str(field).split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _evaluate_node(node, data):
    """Evaluate a single condition node; returns (matched, detail)."""
    if not isinstance(node, dict):
        return False, {"error": "invalid_node"}
    if "operator" in node and "rules" in node:
        op = str(node.get("operator", "and")).lower()
        if op not in ("and", "or"):
            return False, {"error": f"unsupported_operator:{op}"}
        matched = op == "and"
        details = []
        for rule in node.get("rules", []):
            child_matched, child_detail = _evaluate_node(rule, data)
            details.append(child_detail)
            if op == "and" and child_matched:
                matched = False
            elif op == "or" and child_matched:
                matched = True
        return matched, {"operator": op, "matched": matched, "rules": details}
    field = node.get("field")
    operator = str(node.get("operator", "eq")).lower()
    expected = node.get("value")
    if operator not in CONDITION_OPERATORS:
        return False, {"field": field, "operator": operator, "error": "unsupported_operator"}
    actual = _resolve_field(data, field) if field else None
    matched = _compare(actual, operator, expected)
    return matched, {
        "field": field,
        "operator": operator,
        "expected": _json_safe(expected),
        "actual": _json_safe(actual),
        "matched": matched,
    }


def evaluate_conditions(conditions, data: dict) -> dict:
    """Evaluate an AND/OR expression tree. Empty conditions match everything."""
    if not conditions:
        return {"matched": True, "tree": []}
    matched, detail = _evaluate_node(conditions, data)
    return {"matched": matched, "tree": detail}


def get_entity_data(entity, _depth: int = 0) -> dict:
    """Best-effort flattening of common entity attributes for conditions."""
    if entity is None or _depth > 3:
        return {}
    data = {}
    for attr in (
        "id",
        "title",
        "name",
        "email",
        "status",
        "first_name",
        "last_name",
        "full_name",
        "score",
        "overall_score",
    ):
        try:
            value = getattr(entity, attr, None)
            if value is not None:
                data[attr] = _json_safe(value)
        except Exception:  # noqa: BLE001
            continue
    for rel in ("job", "candidate", "stage", "template", "application"):
        try:
            related = getattr(entity, rel, None)
        except Exception:  # noqa: BLE001
            continue
        if related is not None:
            data[rel] = get_entity_data(related, _depth=_depth + 1)
    return data


def load_entity(entity_type: str, entity_id: str, organization=None):
    """Load a domain entity by type/id, scoped to the organization when possible."""
    entry = ENTITY_REGISTRY.get(entity_type)
    if not entry:
        return None
    app_label, model_name = entry
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return None
    qs = model.objects.all()
    if organization is not None and hasattr(model, "organization_id"):
        qs = qs.filter(organization=organization)
    try:
        return qs.filter(pk=entity_id).first()
    except (ValueError, TypeError):
        return None


def _resolve_recipient(user_id, rule: AutomationRule, entity):
    """Pick the notification recipient: explicit user → rule creator → entity user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user is not None:
            return user
    if rule.created_by is not None:
        return rule.created_by
    if entity is not None:
        user = getattr(entity, "user", None)
        if user is not None:
            return user
    raise ValidationError("No recipient resolvable for notification action.")


def _run_action(action_type: str, params: dict, rule: AutomationRule, entity, actor=None) -> dict:
    """Perform the in-system side effect for an action; returns a detail dict."""
    if action_type == "notify":
        recipient = _resolve_recipient(params.get("user_id"), rule, entity)
        from apps.core.notifications import notify_user

        notify_user(
            recipient=recipient,
            title=str(params.get("title") or f"Automation: {rule.name}"),
            body=str(params.get("body") or rule.description or ""),
            organization=rule.organization,
            category="automation",
            link=str(params.get("link") or ""),
            data={"rule_id": str(rule.pk)},
        )
        return {"recipient_id": str(recipient.pk), "queued": True}

    if action_type == "send_email":
        recipient = _resolve_recipient(params.get("user_id") or params.get("to_user_id"), rule, entity)
        from apps.core.notifications import notify_user

        notify_user(
            recipient=recipient,
            title=str(params.get("subject") or f"Automation: {rule.name}"),
            body=str(params.get("body") or ""),
            organization=rule.organization,
            category="automation_email",
            data={"rule_id": str(rule.pk)},
        )
        return {"recipient_id": str(recipient.pk), "queued": True, "channel": "notification"}

    if action_type == "create_task":
        from apps.pipelines.models import Application, AutomatedTask

        if not isinstance(entity, Application):
            raise ValidationError("create_task requires an Application entity context.")
        task = AutomatedTask.objects.create(
            organization=rule.organization,
            application=entity,
            task_type=AutomatedTask.TaskType.CUSTOM,
            status=AutomatedTask.Status.PENDING,
            payload={"source": "automation", "rule_id": str(rule.pk), **params},
            scheduled_for=timezone.now() - timezone.timedelta(days=int(params.get("due_in_days", 0))),
        )
        return {"task_id": str(task.pk), "application_id": str(entity.pk)}

    if action_type == "move_stage":
        from apps.pipelines.models import Application, PipelineStage
        from apps.pipelines.services import move_application

        if not isinstance(entity, Application):
            raise ValidationError("move_stage requires an Application entity context.")
        stage_id = params.get("stage_id")
        if not stage_id:
            raise ValidationError("move_stage requires params.stage_id.")
        stage = PipelineStage.objects.for_org(rule.organization).filter(pk=stage_id).first()
        if stage is None:
            raise ValidationError("Target stage not found in organization.")
        moved = move_application(
            entity,
            stage,
            actor=actor,
            note=f"Automation rule: {rule.name}",
            skip_rules=True,
        )
        return {"application_id": str(moved.pk), "stage_id": str(stage.pk)}

    if action_type == "update_field":
        field = params.get("field")
        value = params.get("value")
        if not field or entity is None:
            raise ValidationError("update_field requires params.field and an entity.")
        if not hasattr(entity, field):
            raise ValidationError(f"Entity has no field '{field}'.")
        setattr(entity, field, value)
        update_fields = [field]
        if hasattr(entity, "updated_at"):
            update_fields.append("updated_at")
        entity.save(update_fields=update_fields)
        return {"field": field, "value": _json_safe(value)}

    if action_type == "send_webhook":
        url = params.get("url")
        if not url:
            raise ValidationError("send_webhook requires params.url.")
        payload = {
            "event": rule.trigger,
            "rule_id": str(rule.pk),
            "rule_name": rule.name,
            "entity_type": entity.__class__.__name__ if entity is not None else None,
            "entity_id": str(getattr(entity, "pk", "") or "") or None,
            "executed_at": timezone.now().isoformat(),
            "params": params,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-HireFlux-Rule": str(rule.pk),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return {"url": url, "status_code": response.status}
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"Webhook request failed: {exc}") from exc

    raise ValidationError(f"Unsupported action type '{action_type}'.")


@transaction.atomic
def _execute_action(
    execution: RuleExecution,
    rule: AutomationRule,
    entity,
    action: dict,
    index: int,
    actor=None,
) -> RuleActionLog:
    action_type = str(action.get("type", "")).strip()
    params = action.get("params") or {}
    log = RuleActionLog.objects.create(
        organization=rule.organization,
        execution=execution,
        action_index=index,
        action_type=action_type,
        status=RuleActionLog.Status.SKIPPED,
        executed_at=timezone.now(),
    )
    if action_type not in SUPPORTED_ACTIONS:
        log.status = RuleActionLog.Status.SKIPPED
        log.detail = {"reason": "unsupported_action_type", "supported": sorted(SUPPORTED_ACTIONS)}
        log.save()
        return log
    try:
        detail = _run_action(action_type, params, rule, entity, actor=actor)
        log.status = RuleActionLog.Status.SUCCESS
        log.detail = detail or {}
        log.save()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Automation action %s failed for rule %s", action_type, rule.pk)
        log.status = RuleActionLog.Status.FAILED
        log.detail = {"error": str(exc)}
        log.save()
    return log


@transaction.atomic
def evaluate_rule_for_event(
    rule: AutomationRule,
    trigger_event: str,
    entity_type: str = "",
    entity_id: str = "",
    entity=None,
    actor=None,
    dry_run: bool = False,
) -> dict:
    """
    Evaluate one rule for a trigger event.

    Returns a plan dict for dry runs; otherwise persists a RuleExecution
    (matched/skipped/failed) and runs actions when conditions match.
    """
    if rule.is_active:
        return {"skipped": "rule_inactive"}
    if rule.trigger != trigger_event:
        return {"skipped": "trigger_mismatch"}

    if entity is None and entity_type and entity_id:
        entity = load_entity(entity_type, entity_id, organization=rule.organization)

    data = get_entity_data(entity) if entity is not None else {}
    conditions_result = evaluate_conditions(rule.conditions or [], data)
    matched = conditions_result["matched"]

    if dry_run:
        return {
            "rule_id": str(rule.pk),
            "rule_name": rule.name,
            "trigger_event": trigger_event,
            "conditions_evaluated": conditions_result,
            "matched": matched,
            "actions": [
                {
                    "index": idx,
                    "type": action.get("type"),
                    "would_run": matched,
                    "params": action.get("params"),
                }
                for idx, action in enumerate(rule.actions or [])
            ],
        }

    execution = RuleExecution.objects.create(
        organization=rule.organization,
        rule=rule,
        trigger_event=trigger_event,
        entity_type=entity_type or (entity.__class__.__name__ if entity else ""),
        entity_id=entity_id or str(getattr(entity, "pk", "") or ""),
        status=RuleExecution.Status.MATCHED if matched else RuleExecution.Status.SKIPPED,
        conditions_evaluated=conditions_result,
        executed_at=timezone.now(),
    )

    if matched:
        rule.run_count += 1
        rule.last_run_at = timezone.now()
        rule.save(update_fields=["run_count", "last_run_at", "updated_at"])
        action_logs = [
            _execute_action(execution, rule, entity, action, idx, actor=actor)
            for idx, action in enumerate(rule.actions or [])
        ]
        return {
            "execution_id": str(execution.pk),
            "status": execution.status,
            "action_logs": [str(log.pk) for log in action_logs],
        }
    return {"execution_id": str(execution.pk), "status": execution.status}


@transaction.atomic
def fire_trigger(
    organization,
    trigger_event: str,
    entity_type: str = "",
    entity_id: str = "",
    entity=None,
    actor=None,
    async_mode: bool = False,
) -> dict:
    """Evaluate every active rule matching a trigger event."""
    rules = AutomationRule.objects.for_org(organization).filter(
        trigger=trigger_event,
        is_active=True,
        is_deleted=False,
    )
    results = []
    for rule in rules.iterator():
        if async_mode:
            from apps.automation.tasks import evaluate_rule_for_event as evaluate_task

            evaluate_task.delay(str(rule.pk), trigger_event, entity_type or "", entity_id or "")
            results.append({"rule_id": str(rule.pk), "queued": True})
        else:
            results.append(
                evaluate_rule_for_event(
                    rule,
                    trigger_event,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity=entity,
                    actor=actor,
                )
            )
    return {
        "trigger_event": trigger_event,
        "rules_evaluated": len(results),
        "results": results,
    }


@transaction.atomic
def test_run(rule: AutomationRule, entity_type: str, entity_id: str) -> dict:
    """Simulate rule evaluation without persisting executions or side effects."""
    return evaluate_rule_for_event(
        rule,
        rule.trigger,
        entity_type=entity_type,
        entity_id=entity_id,
        entity=None,
        dry_run=True,
    )


@transaction.atomic
def duplicate_rule(rule: AutomationRule, actor=None) -> AutomationRule:
    """Clone a rule with a unique name; the copy starts disabled."""
    base_name = f"{rule.name} (copy)"
    name = base_name
    n = 1
    while AutomationRule.all_objects.filter(
        organization=rule.organization, name=name, is_deleted=False
    ).exists():
        n += 1
        name = f"{base_name} {n}"
    cloned = AutomationRule.objects.create(
        organization=rule.organization,
        name=name,
        description=rule.description,
        trigger=rule.trigger,
        trigger_config=copy.deepcopy(rule.trigger_config),
        conditions=copy.deepcopy(rule.conditions),
        actions=copy.deepcopy(rule.actions),
        is_active=False,
        created_by=actor,
        updated_by=actor,
    )
    return cloned
