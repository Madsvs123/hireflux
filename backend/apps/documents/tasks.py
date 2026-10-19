"""
Celery tasks for documents: signer emails, async rendering, expiry sweep.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_sign_request_email(self, sign_request_id: str):
    """Email the signer a link to review and sign the document."""
    from django.core.mail import send_mail

    from apps.documents.models import DocumentSignRequest
    from apps.documents.services import sign_link

    try:
        sign_request = DocumentSignRequest.objects.select_related(
            "document", "organization"
        ).get(pk=sign_request_id)
    except DocumentSignRequest.DoesNotExist:
        logger.warning("send_sign_request_email: sign request %s not found", sign_request_id)
        return {"ok": False, "error": "not_found"}

    try:
        subject = f"Please sign: {sign_request.document.title}"
        body = (
            f"Hi {sign_request.signer_name},\n\n"
            f"{sign_request.message or 'A document is waiting for your signature.'}\n\n"
            f"Review and sign here: {sign_link(sign_request)}\n\n"
            f"This link expires on {sign_request.expires_at.isoformat()}."
        )
        send_mail(
            subject,
            body,
            None,
            [sign_request.signer_email],
            fail_silently=True,
        )
        return {"ok": True, "sign_request_id": str(sign_request.pk)}
    except Exception as exc:
        logger.exception("send_sign_request_email failed for %s", sign_request_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def render_document_async(self, document_id: str, variables: dict | None = None):
    """Re-render a generated document from its template (large documents)."""
    from apps.documents.models import GeneratedDocument
    from apps.documents.services import render_document

    try:
        document = GeneratedDocument.objects.select_related("template").get(pk=document_id)
    except GeneratedDocument.DoesNotExist:
        logger.warning("render_document_async: document %s not found", document_id)
        return {"ok": False, "error": "not_found"}

    template = document.template
    if template is None:
        return {"ok": False, "error": "no_template"}

    try:
        rendered = render_document(template, variables or {})
        document.content_html = rendered["content_html"]
        document.content_text = rendered["content_text"]
        document.save(update_fields=["content_html", "content_text", "updated_at"])
        return {"ok": True, "document_id": str(document.pk)}
    except Exception as exc:
        logger.exception("render_document_async failed for %s", document_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def expire_stale_sign_requests(self):
    """Void pending sign requests past their expiry date."""
    from apps.documents.services import expire_stale_sign_requests

    try:
        count = expire_stale_sign_requests()
        return {"ok": True, "voided": count}
    except Exception as exc:
        logger.exception("expire_stale_sign_requests failed")
        raise self.retry(exc=exc)
