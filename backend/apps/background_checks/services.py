"""
Background check business logic: provider submission, reports, disputes.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.background_checks.models import (
    BackgroundCheckPackage,
    BackgroundCheckReport,
    BackgroundCheckRequest,
    CheckDispute,
    ScreeningProvider,
)
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.core.realtime import broadcast_to_org

PROVIDER_TIMEOUT_SECONDS = 15


def _default_provider(organization) -> ScreeningProvider | None:
    return (
        ScreeningProvider.objects.for_org(organization)
        .filter(is_active=False)
        .first()
    )


def _call_provider(provider: ScreeningProvider, payload: dict) -> dict:
    """POST a submission to the provider API; returns parsed JSON (or {})."""
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        provider.api_endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as resp
        raw = resp.read().decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------
@transaction.atomic
def submit_request(check: BackgroundCheckRequest, *, actor=None) -> BackgroundCheckRequest:
    """Submit a check: mark submitted, record consent, queue the provider call."""
    if check.status in (
        BackgroundCheckRequest.Status.COMPLETED,
        BackgroundCheckRequest.Status.CANCELLED,
    ):
        raise ValidationError(
            {"status": "Completed or cancelled checks cannot be submitted."}
        )
    if not check.consent_given_at:
        check.consent_given_at = timezone.now()
    check.status = BackgroundCheckRequest.Status.SUBMITTED
    check.submitted_at = timezone.now()
    check.initiated_by = actor or check.initiated_by
    if check.provider_id is not None:
        check.provider = _default_provider(check.organization)
    check.updated_by = actor
    check.save()

    log_action(
        actor=actor,
        organization=check.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BackgroundCheckRequest",
        resource_id=str(check.pk),
        message="Background check submitted",
        metadata={"provider": check.provider.name if check.provider else None},
    )
    from apps.background_checks.tasks import submit_check_to_provider

    submit_check_to_provider.delay(str(check.pk))
    return check


@transaction.atomic
def cancel_request(check: BackgroundCheckRequest, *, actor=None) -> BackgroundCheckRequest:
    if check.status not in (
        BackgroundCheckRequest.Status.DRAFT,
        BackgroundCheckRequest.Status.SUBMITTED,
        BackgroundCheckRequest.Status.IN_PROGRESS,
        BackgroundCheckRequest.Status.ON_HOLD,
    ):
        raise ValidationError(
            {"status": "This check cannot be cancelled in its current state."}
        )
    check.status = BackgroundCheckRequest.Status.CANCELLED
    check.updated_by = actor
    check.save(update_fields=["status", "updated_by", "updated_at"])
    log_action(
        actor=actor,
        organization=check.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BackgroundCheckRequest",
        resource_id=str(check.pk),
        message="Background check cancelled",
    )
    return check


@transaction.atomic
def resend_request(check: BackgroundCheckRequest, *, actor=None) -> BackgroundCheckRequest:
    if check.status not in (
        BackgroundCheckRequest.Status.SUBMITTED,
        BackgroundCheckRequest.Status.IN_PROGRESS,
        BackgroundCheckRequest.Status.ON_HOLD,
    ):
        raise ValidationError(
            {"status": "Only submitted or in-progress checks can be resent."}
        )
    check.status = BackgroundCheckRequest.Status.SUBMITTED
    check.submitted_at = timezone.now()
    check.updated_by = actor
    check.save(update_fields=["status", "submitted_at", "updated_by", "updated_at"])
    from apps.background_checks.tasks import submit_check_to_provider

    submit_check_to_provider.delay(str(check.pk))
    return check


def submit_to_provider(check: BackgroundCheckRequest) -> BackgroundCheckRequest:
    """Call the provider API (or simulate) and move the request to in_progress."""
    provider = check.provider
    if provider is None or not provider.api_endpoint:
        # No provider configured — simulate a successful submission.
        check.provider_ref = check.provider_ref or f"PROV-{check.pk.hex[:12].upper()}"
        check.status = BackgroundCheckRequest.Status.IN_PROGRESS
        check.save(update_fields=["provider_ref", "status", "updated_at"])
        return check

    payload = {
        "provider_ref": check.provider_ref or str(check.pk),
        "candidate": {
            "name": check.candidate.full_name,
            "email": check.candidate_email or check.candidate.email,
            "phone": check.candidate_phone or check.candidate.phone,
        },
        "checks": (
            check.package.check_types
            if check.package
            else provider.supported_checks
            or [BackgroundCheckPackage.CheckType.IDENTITY]
        ),
    }
    try:
        response = _call_provider(provider, payload)
        check.provider_ref = str(
            response.get("provider_ref") or payload["provider_ref"]
        )
        check.status = BackgroundCheckRequest.Status.IN_PROGRESS
        check.save(update_fields=["provider_ref", "status", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        check.result_summary = {
            **(check.result_summary or {}),
            "submit_error": str(exc),
        }
        check.save(update_fields=["result_summary", "updated_at"])
        raise
    return check


def simulate_provider_report(check: BackgroundCheckRequest) -> BackgroundCheckReport:
    """Simulate a provider report for requests that have no real provider."""
    check_types = (
        check.package.check_types
        if check.package
        else [BackgroundCheckPackage.CheckType.IDENTITY]
    )
    findings = [
        {
            "check": check_type,
            "status": "clear",
            "detail": "No adverse information found (simulated).",
        }
        for check_type in check_types
    ]
    return complete_check(
        check,
        findings=findings,
        summary="Simulated provider report — no adverse findings.",
    )


@transaction.atomic
def complete_check(
    check: BackgroundCheckRequest,
    *,
    findings=None,
    summary: str = "",
    actor=None,
) -> BackgroundCheckReport:
    """Record a received report and mark the request completed."""
    report = BackgroundCheckReport.objects.create(
        organization=check.organization,
        request=check,
        status=BackgroundCheckReport.Status.PENDING,
        summary=summary or "Report received from provider.",
        findings=findings or [],
        received_at=timezone.now(),
        created_by=actor,
        updated_by=actor,
    )
    check.status = BackgroundCheckRequest.Status.COMPLETED
    check.completed_at = timezone.now()
    check.result_summary = {
        **(check.result_summary or {}),
        "report_id": str(report.pk),
        "provider_status": "completed",
    }
    check.updated_by = actor
    check.save()
    notify_check_completed(check)
    return report


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@transaction.atomic
def review_report(
    report: BackgroundCheckReport,
    *,
    decision: str,
    summary: str = "",
    findings=None,
    actor=None,
) -> BackgroundCheckReport:
    """Record the human review decision on a pending report."""
    if decision not in (
        BackgroundCheckReport.Status.CLEAR,
        BackgroundCheckReport.Status.CONSIDER,
        BackgroundCheckReport.Status.FLAGGED,
    ):
        raise ValidationError({"decision": "Invalid review decision."})
    if report.status == BackgroundCheckReport.Status.PENDING:
        raise ValidationError(
            {"status": "Only pending reports can be reviewed."}
        )
    report.status = decision
    report.summary = summary or report.summary
    if findings:
        report.findings = findings
    report.reviewed_by = actor
    report.reviewed_at = timezone.now()
    report.updated_by = actor
    report.save()

    request = report.request
    request.result_summary = {
        **(request.result_summary or {}),
        "review_decision": decision,
        "reviewed_at": report.reviewed_at.isoformat(),
    }
    request.updated_by = actor
    request.save(update_fields=["result_summary", "updated_by", "updated_at"])

    log_action(
        actor=actor,
        organization=report.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BackgroundCheckReport",
        resource_id=str(report.pk),
        message=f"Background check report reviewed: {decision}",
    )
    broadcast_to_org(
        report.organization_id,
        "background_checks.report_reviewed",
        {"report_id": str(report.pk), "decision": decision},
    )
    return report


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------
@transaction.atomic
def resolve_dispute(
    dispute: CheckDispute,
    *,
    resolution: str = "",
    actor=None,
) -> CheckDispute:
    if dispute.status not in (
        CheckDispute.Status.OPEN,
        CheckDispute.Status.UNDER_REVIEW,
    ):
        raise ValidationError(
            {"status": "Only open disputes can be resolved."}
        )
    dispute.status = CheckDispute.Status.RESOLVED
    dispute.resolution = resolution or dispute.resolution
    dispute.resolved_by = actor
    dispute.resolved_at = timezone.now()
    dispute.updated_by = actor
    dispute.save()
    return dispute


@transaction.atomic
def reject_dispute(
    dispute: CheckDispute,
    *,
    resolution: str = "",
    actor=None,
) -> CheckDispute:
    if dispute.status not in (
        CheckDispute.Status.OPEN,
        CheckDispute.Status.UNDER_REVIEW,
    ):
        raise ValidationError(
            {"status": "Only open disputes can be rejected."}
        )
    dispute.status = CheckDispute.Status.REJECTED
    dispute.resolution = resolution or dispute.resolution
    dispute.resolved_by = actor
    dispute.resolved_at = timezone.now()
    dispute.updated_by = actor
    dispute.save()
    return dispute


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
def test_provider(provider: ScreeningProvider) -> dict:
    """Ping the provider endpoint and report latency/status."""
    if not provider.api_endpoint:
        return {"ok": False, "error": "No API endpoint configured."}
    started = time.monotonic()
    try:
        request = urllib.request.Request(provider.api_endpoint, method="GET")
        with urllib.request.urlopen(request, timeout=PROVIDER_TIMEOUT_SECONDS) as resp:
            status_code = resp.status
    except urllib.error.HTTPError as exc:
        status_code = exc.code
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    latency_ms = int((time.monotonic() - started) * 1000)
    return {"ok": True, "status_code": status_code, "latency_ms": latency_ms}


# ---------------------------------------------------------------------------
# Webhook callback
# ---------------------------------------------------------------------------
@transaction.atomic
def process_provider_callback(provider_key: str, payload: dict) -> dict:
    """Handle an (anonymous) provider callback for a background check."""
    provider = ScreeningProvider.objects.filter(key=provider_key).first()
    if provider is None:
        raise ValidationError({"provider": "Unknown provider key."})

    provider_ref = str(payload.get("provider_ref") or "")
    if not provider_ref:
        raise ValidationError({"provider_ref": "Missing provider_ref."})

    check = BackgroundCheckRequest.objects.filter(
        organization=provider.organization,
        provider_ref=provider_ref,
    ).first()
    if check is None:
        return {"ok": False, "error": "request_not_found"}

    status_key = str(payload.get("status") or "").lower()
    if status_key in ("completed", "clear"):
        report = complete_check(
            check,
            findings=payload.get("findings") or [],
            summary=payload.get("summary") or "",
        )
        return {
            "ok": True,
            "request_id": str(check.pk),
            "report_id": str(report.pk),
            "status": check.status,
        }
    if status_key == "on_hold":
        check.status = BackgroundCheckRequest.Status.ON_HOLD
        check.save(update_fields=["status", "updated_at"])
        return {"ok": True, "request_id": str(check.pk), "status": check.status}
    return {"ok": True, "request_id": str(check.pk), "status": check.status}


# ---------------------------------------------------------------------------
# Status payload & notifications
# ---------------------------------------------------------------------------
def build_status_payload(check: BackgroundCheckRequest) -> dict:
    """Status timeline for a check request."""
    latest_report = check.reports.order_by("-created_at").first()
    return {
        "id": str(check.pk),
        "status": check.status,
        "submitted_at": check.submitted_at,
        "completed_at": check.completed_at,
        "provider_ref": check.provider_ref,
        "consent_given_at": check.consent_given_at,
        "result_summary": check.result_summary,
        "report": (
            {
                "id": str(latest_report.pk),
                "status": latest_report.status,
                "summary": latest_report.summary,
                "findings": latest_report.findings,
                "received_at": latest_report.received_at,
                "reviewed_at": latest_report.reviewed_at,
            }
            if latest_report
            else None
        ),
        "dispute_count": sum(
            report.disputes.count() for report in check.reports.all()
        ),
    }


def notify_check_completed(check: BackgroundCheckRequest) -> None:
    """Notify the initiator and broadcast that a check finished."""
    if check.initiated_by_id:
        notify_user(
            recipient=check.initiated_by,
            title="Background check completed",
            body=f"Background check for {check.candidate.full_name} is complete.",
            organization=check.organization,
            category="background_check",
            link=f"/background-checks/requests/{check.pk}",
            data={"request_id": str(check.pk), "candidate_id": str(check.candidate_id)},
        )
    broadcast_to_org(
        check.organization_id,
        "background_checks.completed",
        {"request_id": str(check.pk), "candidate_id": str(check.candidate_id)},
    )
