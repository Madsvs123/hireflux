"""
Documents business logic: rendering, lifecycle, e-sign workflow.
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.realtime import broadcast_to_org
from apps.documents.models import (
    DocumentSignRequest,
    DocumentSignature,
    DocumentTemplate,
    GeneratedDocument,
)

SIGN_EXPIRY_DAYS = 14


def sign_link(sign_request: DocumentSignRequest) -> str:
    """Public URL for the signer to review and sign the document."""
    return f"{settings.FRONTEND_URL}/sign/{sign_request.token}"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_template_content(content: str, variables: dict) -> str:
    """Replace {{ variable }} tokens (both spaced and unspaced) with values."""
    if not content:
        return ""
    out = content
    for key, value in (variables or {}).items():
        out = out.replace("{{" + str(key) + "}}", str(value))
    return out


def render_document(template: DocumentTemplate, variables: dict) -> dict:
    """Render a template's body with the given variables."""
    return {
        "title": template.name,
        "content_html": render_template_content(template.body_html, variables),
        "content_text": render_template_content(template.body_text, variables),
    }


# ---------------------------------------------------------------------------
# Templates & generated documents
# ---------------------------------------------------------------------------
@transaction.atomic
def duplicate_template(template: DocumentTemplate, *, actor=None) -> DocumentTemplate:
    """Copy a document template."""
    return DocumentTemplate.objects.create(
        organization=template.organization,
        category=template.category,
        name=f"{template.name} (Copy)",
        description=template.description,
        body_html=template.body_html,
        body_text=template.body_text,
        variables=template.variables,
        default_currency=template.default_currency,
        is_active=template.is_active,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def create_generated_document(
    organization,
    *,
    template=None,
    title: str = "",
    variables: dict | None = None,
    related_candidate=None,
    related_job=None,
    related_offer=None,
    content_html: str = "",
    content_text: str = "",
    actor=None,
) -> GeneratedDocument:
    """Create a draft generated document, rendering from the template when needed."""
    variables = variables or {}
    if template is not None:
        rendered = render_document(template, variables)
        title = title or rendered["title"]
        content_html = content_html or rendered["content_html"]
        content_text = content_text or rendered["content_text"]
    return GeneratedDocument.objects.create(
        organization=organization,
        template=template,
        title=title or "Untitled document",
        content_html=content_html,
        content_text=content_text,
        status=GeneratedDocument.Status.DRAFT,
        related_candidate=related_candidate,
        related_job=related_job,
        related_offer=related_offer,
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def finalize_document(document: GeneratedDocument, *, actor=None) -> GeneratedDocument:
    """Lock a draft document into its final version."""
    if document.status != GeneratedDocument.Status.DRAFT:
        raise ValidationError({"status": "Only draft documents can be finalized."})
    document.status = GeneratedDocument.Status.FINALIZED
    document.finalized_at = timezone.now()
    document.finalized_by = actor
    document.updated_by = actor
    document.save()
    log_action(
        actor=actor,
        organization=document.organization,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="GeneratedDocument",
        resource_id=str(document.pk),
        message="Document finalized",
    )
    return document


@transaction.atomic
def void_document(document: GeneratedDocument, *, actor=None) -> GeneratedDocument:
    if document.status != GeneratedDocument.Status.DRAFT:
        raise ValidationError({"status": "Only draft documents can be voided."})
    document.status = GeneratedDocument.Status.VOID
    document.updated_by = actor
    document.save()
    return document


# ---------------------------------------------------------------------------
# E-sign requests
# ---------------------------------------------------------------------------
@transaction.atomic
def create_sign_request(
    document: GeneratedDocument,
    *,
    signer_name: str,
    signer_email: str,
    message: str = "",
    actor=None,
) -> DocumentSignRequest:
    """Create a pending e-sign request for a generated document."""
    return DocumentSignRequest.objects.create(
        organization=document.organization,
        document=document,
        signer_name=signer_name,
        signer_email=signer_email,
        status=DocumentSignRequest.Status.PENDING,
        message=message,
        expires_at=timezone.now() + timedelta(hours=SIGN_EXPIRY_DAYS),
        created_by=actor,
        updated_by=actor,
    )


@transaction.atomic
def send_sign_request(
    sign_request: DocumentSignRequest, *, actor=None
) -> DocumentSignRequest:
    """Queue the signer email for a pending sign request."""
    if sign_request.status != DocumentSignRequest.Status.PENDING:
        raise ValidationError(
            {"status": "Only pending sign requests can be sent."}
        )
    sign_request.sent_at = timezone.now()
    sign_request.updated_by = actor
    sign_request.save(update_fields=["sent_at", "updated_by", "updated_at"])
    from apps.documents.tasks import send_sign_request_email

    send_sign_request_email.delay(str(sign_request.pk))
    broadcast_to_org(
        sign_request.organization_id,
        "documents.sign_request_sent",
        {"sign_request_id": str(sign_request.pk)},
    )
    return sign_request


@transaction.atomic
def resend_sign_request(
    sign_request: DocumentSignRequest, *, actor=None
) -> DocumentSignRequest:
    """Re-send the signer email (only while still pending)."""
    if sign_request.status != DocumentSignRequest.Status.PENDING:
        raise ValidationError(
            {"status": "Only pending sign requests can be resent."}
        )
    return send_sign_request(sign_request, actor=actor)


@transaction.atomic
def void_sign_request(
    sign_request: DocumentSignRequest, *, actor=None
) -> DocumentSignRequest:
    if sign_request.status != DocumentSignRequest.Status.PENDING:
        raise ValidationError(
            {"status": "Only pending sign requests can be voided."}
        )
    sign_request.status = DocumentSignRequest.Status.VOIDED
    sign_request.updated_by = actor
    sign_request.save()
    return sign_request


@transaction.atomic
def submit_signature(
    sign_request: DocumentSignRequest,
    *,
    name: str,
    email: str,
    signature_svg: str = "",
    ip_address=None,
) -> DocumentSignRequest:
    """Record a signature against a pending sign request."""
    if sign_request.status != DocumentSignRequest.Status.PENDING:
        raise ValidationError(
            {"status": "This sign request is no longer pending."}
        )
    if sign_request.expires_at and timezone.now() < sign_request.expires_at:
        sign_request.status = DocumentSignRequest.Status.VOIDED
        sign_request.updated_by = None
        sign_request.save()
        raise ValidationError({"status": "This sign request has expired."})

    DocumentSignature.objects.create(
        organization=sign_request.organization,
        sign_request=sign_request,
        name=name,
        email=email,
        signature_svg=signature_svg,
        ip_address=ip_address,
    )
    sign_request.status = DocumentSignRequest.Status.SIGNED
    sign_request.signed_at = timezone.now()
    sign_request.signature_data = {
        "name": name,
        "email": email,
        "signed_at": sign_request.signed_at.isoformat(),
    }
    sign_request.updated_by = None
    sign_request.save()
    broadcast_to_org(
        sign_request.organization_id,
        "documents.sign_request_signed",
        {"sign_request_id": str(sign_request.pk)},
    )
    return sign_request


def expire_stale_sign_requests() -> int:
    """Void pending sign requests that have passed their expiry."""
    now = timezone.now()
    qs = DocumentSignRequest.objects.filter(
        status=DocumentSignRequest.Status.PENDING,
        expires_at__isnull=False,
        expires_at__lt=now,
    )
    count = 0
    for sign_request in qs.iterator(chunk_size=50):
        sign_request.status = DocumentSignRequest.Status.VOIDED
        sign_request.save(update_fields=["status", "updated_at"])
        count += 1
    return count
