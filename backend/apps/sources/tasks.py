"""
Celery tasks for sourcing campaigns and source metric rollups.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_campaign_emails(self, campaign_id: str):
    """Deliver campaign emails to every queued recipient."""
    from apps.sources.models import SourcingCampaign
    from apps.sources.services import (
        campaign_recipients_for_send,
        send_recipient_email,
    )

    try:
        campaign = SourcingCampaign.objects.get(pk=campaign_id)
    except SourcingCampaign.DoesNotExist:
        logger.warning("send_campaign_emails: campaign %s not found", campaign_id)
        return {"ok": False, "error": "not_found"}

    sent = 0
    errors = []
    for recipient in campaign_recipients_for_send(campaign).iterator():
        try:
            send_recipient_email(recipient)
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("send_campaign_emails failed for recipient %s", recipient.pk)
            raise self.retry(exc=exc)
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "sent": sent,
        "errors": len(errors),
        "error_samples": errors[:20],
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def send_recipient_email_task(self, recipient_id: str):
    """Deliver a single recipient email with retry."""
    from apps.sources.models import CampaignRecipient
    from apps.sources.services import send_recipient_email

    try:
        recipient = CampaignRecipient.objects.select_related("campaign").get(pk=recipient_id)
    except CampaignRecipient.DoesNotExist:
        logger.warning("send_recipient_email_task: recipient %s not found", recipient_id)
        return {"ok": False, "error": "not_found"}
    try:
        recipient = send_recipient_email(recipient)
        return {"ok": True, "recipient_id": recipient_id, "status": recipient.status}
    except Exception as exc:  # noqa: BLE001
        logger.exception("send_recipient_email_task failed for %s", recipient_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def rollup_source_metrics(self, organization_id: str):
    """Daily aggregation of sourcing activity per organization."""
    from apps.organizations.models import Organization
    from apps.sources.services import rollup_source_metrics as rollup

    try:
        organization = Organization.objects.get(pk=organization_id)
    except Organization.DoesNotExist:
        logger.warning("rollup_source_metrics: organization %s not found", organization_id)
        return {"ok": False, "error": "not_found"}
    try:
        summary = rollup(organization)
        return {"ok": True, **summary}
    except Exception as exc:  # noqa: BLE001
        logger.exception("rollup_source_metrics failed for %s", organization_id)
        raise self.retry(exc=exc)
