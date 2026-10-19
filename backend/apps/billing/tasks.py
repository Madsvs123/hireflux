"""
Celery tasks for invoice generation, emailing, dunning, and usage
aggregation.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_monthly_invoices():
    """Beat-driven renewal pass for subscriptions."""
    from apps.billing.services import process_subscription_renewals

    stats = process_subscription_renewals()
    logger.info("generate_monthly_invoices: %s", stats)
    return stats


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invoice_emails(self, invoice_id: str):
    """Email a single invoice to the organization owners."""
    from apps.billing.models import Invoice
    from apps.billing.services import send_invoice_email

    try:
        invoice = Invoice.objects.select_related("organization").get(pk=invoice_id)
    except Invoice.DoesNotExist:
        logger.warning("send_invoice_emails: invoice %s not found", invoice_id)
        return {"ok": False, "error": "not_found"}

    try:
        sent = send_invoice_email(invoice)
        return {"ok": True, "invoice_id": invoice_id, "sent": sent}
    except Exception as exc:  # noqa: BLE001
        logger.exception("send_invoice_emails failed for %s", invoice_id)
        raise self.retry(exc=exc)


@shared_task
def dunning_reminders():
    """Remind on overdue invoices; write off long-overdue ones."""
    from apps.billing.services import process_dunning

    stats = process_dunning()
    logger.info("dunning_reminders: %s", stats)
    return stats


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def aggregate_usage(self, organization_id: str | None = None):
    """Aggregate usage for one org, or every org when no id is given."""
    from apps.organizations.models import Organization

    from apps.billing.services import aggregate_org_usage

    if organization_id:
        try:
            org = Organization.objects.get(pk=organization_id)
        except Organization.DoesNotExist:
            logger.warning("aggregate_usage: org %s not found", organization_id)
            return {"ok": False, "error": "org_not_found"}
        orgs = [org]
    else:
        orgs = list(Organization.objects.filter(is_deleted=False).only("pk"))

    results = []
    for org in orgs:
        try:
            records = aggregate_org_usage(org)
            results.append(
                {
                    "organization_id": str(org.pk),
                    "records": [str(r.pk) for r in records],
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("aggregate_usage failed for org %s", org.pk)
            raise self.retry(exc=exc)
    return {"ok": True, "organizations": results}
