"""
Compliance business logic: policies, consents, retention sweeps, EEO, exports.
"""
from __future__ import annotations

import json
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.compliance.models import (
    ComplianceNote,
    CompliancePolicy,
    ConsentRecord,
    DataExportRequest,
    DataRetentionPolicy,
    EEODeclaration,
)
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.realtime import broadcast_to_org


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
@transaction.atomic
def activate_policy(policy: CompliancePolicy, *, actor=None) -> CompliancePolicy:
    """Activate a policy; deactivate siblings; bump consent policy versions."""
    if policy.policy_type != CompliancePolicy.PolicyType.CONSENT:
        policy.version += 1
    CompliancePolicy.objects.for_org(policy.organization).filter(
        policy_type=policy.policy_type,
        is_active=True,
    ).exclude(pk=policy.pk).update(is_active=False)
    policy.is_active = True
    policy.effective_at = timezone.now()
    policy.updated_by = actor
    policy.save()
    log_action(
        actor=actor,
        organization=policy.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CompliancePolicy",
        resource_id=str(policy.pk),
        message=f"Compliance policy activated (v{policy.version})",
    )
    broadcast_to_org(
        policy.organization_id,
        "compliance.policy_activated",
        {"policy_id": str(policy.pk), "policy_type": policy.policy_type},
    )
    return policy


# ---------------------------------------------------------------------------
# Consents
# ---------------------------------------------------------------------------
@transaction.atomic
def grant_consent(
    organization,
    *,
    policy: CompliancePolicy,
    candidate=None,
    user=None,
    purpose: str = "",
    source: str = "",
    ip_address=None,
    actor=None,
) -> ConsentRecord:
    """Grant consent against an active consent policy."""
    if policy.policy_type != CompliancePolicy.PolicyType.CONSENT:
        raise ValidationError(
            {"policy": "Consent can only be granted against consent policies."}
        )
    if not policy.is_active:
        raise ValidationError({"policy": "Policy is not active."})
    if candidate is None and user is None:
        raise ValidationError(
            {"candidate": "Provide candidate_id or user_id."}
        )
    record = ConsentRecord.objects.create(
        organization=organization,
        candidate=candidate,
        user=user,
        policy=policy,
        purpose=purpose or policy.name,
        status=ConsentRecord.Status.GRANTED,
        source=source,
        ip_address=ip_address,
        consent_version=policy.version,
        created_by=actor,
        updated_by=actor,
    )
    log_action(
        actor=actor,
        organization=organization,
        action=AuditLog.Action.CREATE,
        resource_type="ConsentRecord",
        resource_id=str(record.pk),
        message=f"Consent granted: {record.purpose}",
        metadata={"policy_id": str(policy.pk), "version": policy.version},
    )
    return record


@transaction.atomic
def withdraw_consent(record: ConsentRecord, *, actor=None) -> ConsentRecord:
    if record.status != ConsentRecord.Status.GRANTED:
        raise ValidationError({"status": "Consent is not currently granted."})
    record.status = ConsentRecord.Status.WITHDRAWN
    record.withdrawn_at = timezone.now()
    record.updated_by = actor
    record.save()
    log_action(
        actor=actor,
        organization=record.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="ConsentRecord",
        resource_id=str(record.pk),
        message="Consent withdrawn",
    )
    return record


def expire_consents() -> int:
    """Withdraw granted consents that predate the active policy version."""
    count = 0
    for policy in CompliancePolicy.objects.filter(
        policy_type=CompliancePolicy.PolicyType.CONSENT,
        is_active=True,
    ):
        stale = ConsentRecord.objects.filter(
            policy=policy,
            status=ConsentRecord.Status.GRANTED,
            consent_version__lte=policy.version,
        )
        for record in stale.iterator(chunk_size=50):
            record.status = ConsentRecord.Status.WITHDRAWN
            record.withdrawn_at = timezone.now()
            record.save(update_fields=["status", "withdrawn_at", "updated_at"])
            count += 1
    return count


# ---------------------------------------------------------------------------
# EEO declarations
# ---------------------------------------------------------------------------
@transaction.atomic
def create_declaration(
    organization,
    *,
    candidate=None,
    job=None,
    actor=None,
) -> EEODeclaration:
    """Create an EEO declaration shell (filled in by anonymous token submit)."""
    return EEODeclaration.objects.create(
        organization=organization,
        candidate=candidate,
        job=job,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def submit_eeo(
    declaration: EEODeclaration,
    *,
    gender: str = "",
    race_ethnicity: str = "",
    veteran_status: str = "",
    disability_status: str = "",
    ip_address=None,
) -> EEODeclaration:
    """Fill in an EEO declaration anonymously via its token."""
    if declaration.submitted_at:
        raise ValidationError(
            {"status": "Declaration has already been submitted."}
        )
    if not any([gender, race_ethnicity, veteran_status, disability_status]):
        raise ValidationError(
            {"detail": "Provide at least one EEO answer."}
        )
    declaration.gender = gender
    declaration.race_ethnicity = race_ethnicity
    declaration.veteran_status = veteran_status
    declaration.disability_status = disability_status
    declaration.submitted_at = timezone.now()
    declaration.is_anonymous = True
    declaration.save()
    broadcast_to_org(
        declaration.organization_id,
        "compliance.eeo_submitted",
        {"declaration_id": str(declaration.pk)},
    )
    return declaration


# ---------------------------------------------------------------------------
# Data exports
# ---------------------------------------------------------------------------
@transaction.atomic
def queue_export_fulfillment(
    export_request: DataExportRequest, *, actor=None
) -> DataExportRequest:
    """Mark an export request as processing and queue the Celery task."""
    if export_request.status not in (
        DataExportRequest.Status.PENDING,
        DataExportRequest.Status.FAILED,
    ):
        raise ValidationError(
            {"status": "Export request is already being processed."}
        )
    export_request.status = DataExportRequest.Status.PROCESSING
    export_request.updated_by = actor
    export_request.save(update_fields=["status", "updated_by", "updated_at"])
    from apps.compliance.tasks import fulfill_data_export

    fulfill_data_export.delay(str(export_request.pk))
    return export_request


def build_export_payload(export_request: DataExportRequest) -> dict:
    """Assemble the candidate data payload for an export request."""
    candidate = export_request.candidate
    include_fields = export_request.include_fields or []
    allowed = {
        "profile",
        "education",
        "experience",
        "documents",
        "applications",
        "offers",
        "interviews",
        "assessments",
        "consents",
        "compliance_notes",
    }

    def _wanted(key):
        if not include_fields:
            return True
        return key in allowed

    payload = {"candidate_id": str(candidate.pk), "exported_at": timezone.now().isoformat()}

    if _wanted("profile"):
        payload["profile"] = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "headline": candidate.headline,
            "summary": candidate.summary,
            "skills": candidate.skills,
            "source": candidate.source,
            "created_at": candidate.created_at.isoformat(),
        }
    if _wanted("education"):
        payload["education"] = [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
            }
            for e in candidate.education.all()
        ]
    if _wanted("experience"):
        payload["experience"] = [
            {
                "company": e.company,
                "title": e.title,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "description": e.description,
            }
            for e in candidate.experience.all()
        ]
    if _wanted("documents"):
        payload["documents"] = [
            {
                "title": d.title,
                "doc_type": d.doc_type,
                "file_name": d.file_name,
                "uploaded_at": d.created_at.isoformat(),
            }
            for d in candidate.documents.all()
        ]
    if _wanted("applications"):
        payload["applications"] = [
            {
                "job_title": a.job.title if a.job_id else None,
                "status": a.status,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            }
            for a in candidate.applications.all()
        ]
    if _wanted("offers"):
        payload["offers"] = [
            {
                "title": o.title,
                "status": o.status,
                "salary": str(o.salary) if o.salary is not None else None,
                "created_at": o.created_at.isoformat(),
            }
            for o in candidate.offers.all()
        ]
    if _wanted("interviews"):
        payload["interviews"] = [
            {
                "title": i.title,
                "status": i.status,
                "scheduled_start": i.scheduled_start.isoformat()
                if i.scheduled_start
                else None,
            }
            for i in candidate.interviews.all()
        ]
    if _wanted("assessments"):
        payload["assessments"] = [
            {
                "template": a.template.name if a.template_id else None,
                "status": a.status,
                "score": a.score,
                "created_at": a.created_at.isoformat(),
            }
            for a in candidate.assessment_assignments.all()
        ]
    if _wanted("consents"):
        payload["consents"] = [
            {
                "policy": c.policy.name,
                "purpose": c.purpose,
                "status": c.status,
                "granted_at": c.granted_at.isoformat(),
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            }
            for c in candidate.consent_records.all()
        ]
    if _wanted("compliance_notes"):
        payload["compliance_notes"] = [
            {
                "category": n.category,
                "body": n.body,
                "created_at": n.created_at.isoformat(),
            }
            for n in candidate.compliance_notes.all()
        ]
    return payload


def write_export_file(export_request: DataExportRequest) -> str:
    """Write the export payload to a JSON file and return its path."""
    from django.core.files.base import ContentFile

    payload = build_export_payload(export_request)
    content = json.dumps(payload, indent=2, default=str)
    filename = f"candidate-export-{export_request.pk.hex[:8]}.json"
    export_request.export_file.save(filename, ContentFile(content.encode("utf-8")))
    return export_request.export_file.name


# ---------------------------------------------------------------------------
# Retention sweep
# ---------------------------------------------------------------------------
def _retention_queryset(policy: DataRetentionPolicy):
    """Resolve the model queryset for a retention policy's data type."""
    from django.apps import apps as django_apps

    cutoff = timezone.now() + timedelta(days=policy.retention_days)
    mapping = {
        DataRetentionPolicy.DataType.CANDIDATES: (
            "candidates",
            "Candidate",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.APPLICATIONS: (
            "pipelines",
            "Application",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.DOCUMENTS: (
            "candidates",
            "CandidateDocument",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.MESSAGES: (
            "comms",
            "Message",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.AUDIT_LOGS: (
            "core",
            "AuditLog",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.OFFERS: (
            "offers",
            "Offer",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.INTERVIEWS: (
            "interviews",
            "Interview",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.ASSESSMENTS: (
            "assessments",
            "AssessmentAssignment",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.COMPLIANCE_NOTES: (
            "compliance",
            "ComplianceNote",
            {"created_at__lt": cutoff},
        ),
        DataRetentionPolicy.DataType.CONSENT_RECORDS: (
            "compliance",
            "ConsentRecord",
            {"granted_at__lt": cutoff},
        ),
    }
    entry = mapping.get(policy.data_type)
    if entry is None:
        return None
    app_label, model_name, filters = entry
    model = django_apps.get_model(app_label, model_name)
    qs = model.objects.filter(organization=policy.organization, **filters)
    if hasattr(model, "is_deleted"):
        qs = qs.filter(is_deleted=False)
    return qs


def run_retention_sweep() -> dict:
    """Apply all active retention policies to their data types."""
    summary = {"anonymized": 0, "deleted": 0, "archived": 0, "skipped": []}
    for policy in DataRetentionPolicy.objects.filter(is_active=True):
        qs = _retention_queryset(policy)
        if qs is None:
            summary["skipped"].append(policy.data_type)
            continue
        count = 0
        for instance in qs.iterator(chunk_size=100):
            try:
                if policy.action == DataRetentionPolicy.Action.ANONYMIZE:
                    anonymize_candidate(instance)
                    summary["anonymized"] += 1
                else:
                    # DELETE and ARCHIVE both soft-delete (archive keeps metadata flag).
                    if policy.action == DataRetentionPolicy.Action.ARCHIVE:
                        _archive_instance(instance)
                    else:
                        instance.delete()
                    summary["deleted" if policy.action = DataRetentionPolicy.Action.DELETE else "archived"] += 1
                count += 1
            except Exception:  # noqa: BLE001
                continue
    return summary


def _archive_instance(instance) -> None:
    """Archive a record: soft-delete and flag it in custom_fields if available."""
    if hasattr(instance, "delete"):
        instance.delete()
    if hasattr(instance, "custom_fields") and isinstance(instance.custom_fields, dict):
        instance.custom_fields = {**(instance.custom_fields or {}), "archived": True}
        instance.save(update_fields=["custom_fields", "updated_at"])


@transaction.atomic
def anonymize_candidate(candidate) -> None:
    """Strip PII from a candidate record (idempotent)."""
    candidate.first_name = "Anonymous"
    candidate.last_name = ""
    candidate.email = f"anon-{uuid.uuid4().hex[:12]}@anonymized.local"
    candidate.phone = ""
    candidate.location = ""
    candidate.linkedin_url = ""
    candidate.portfolio_url = ""
    candidate.github_url = ""
    candidate.website_url = ""
    candidate.headline = ""
    candidate.summary = ""
    candidate.custom_fields = {**(candidate.custom_fields or {}), "anonymized": True}
    candidate.save()


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def compliance_overview(organization) -> dict:
    """Aggregate compliance dashboard stats for the organization."""
    consent_qs = ConsentRecord.objects.for_org(organization)
    policies = CompliancePolicy.objects.for_org(organization)
    exports = DataExportRequest.objects.for_org(organization)
    return {
        "consents": {
            "granted": consent_qs.filter(status=ConsentRecord.Status.GRANTED).count(),
            "withdrawn": consent_qs.filter(status=ConsentRecord.Status.WITHDRAWN).count(),
        },
        "policies": {
            "active": policies.filter(is_active=True).count(),
            "total": policies.count(),
            "by_type": {
                policy_type: policies.filter(policy_type=policy_type).count()
                for policy_type in CompliancePolicy.PolicyType.values
            },
        },
        "retention": {
            "active_policies": DataRetentionPolicy.objects.for_org(organization)
            .filter(is_active=True)
            .count(),
        },
        "exports": {
            status_value: exports.filter(status=status_value).count()
            for status_value in DataExportRequest.Status.values
        },
        "eeo_declarations": EEODeclaration.objects.for_org(organization).count(),
    }
