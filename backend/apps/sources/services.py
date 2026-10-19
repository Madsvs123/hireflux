"""
Sourcing services: campaign lifecycle, recipient delivery, attribution stats.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.sources.models import (
    CampaignRecipient,
    CandidateSourceAttribution,
    SourceChannel,
    SourcingCampaign,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Channel stats
# ---------------------------------------------------------------------------


def channel_stats(organization) -> list[dict]:
    """Aggregate campaign/recipient/attribution counts per channel."""
    channels = SourceChannel.objects.for_org(organization).order_by("name")
    rows = []
    for channel in channels:
        campaigns = SourcingCampaign.objects.filter(channel=channel, is_deleted=False)
        recipients = CampaignRecipient.objects.filter(
            campaign__channel=channel, is_deleted=False
        )
        attributions = CandidateSourceAttribution.objects.filter(
            channel=channel, is_deleted=False
        )
        rows.append(
            {
                "channel_id": str(channel.pk),
                "channel": channel.name,
                "channel_type": channel.channel_type,
                "is_active": channel.is_active,
                "cost_per_post": str(channel.cost_per_post) if channel.cost_per_post else None,
                "campaigns": campaigns.count(),
                "active_campaigns": campaigns.filter(status=SourcingCampaign.Status.ACTIVE).count(),
                "recipients": recipients.filter(status=CampaignRecipient.Status.SENT).count(),
                "attributions": attributions.count(),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Campaign lifecycle
# ---------------------------------------------------------------------------


@transaction.atomic
def launch_campaign(campaign: SourcingCampaign, *, actor=None) -> SourcingCampaign:
    """Move a draft campaign to active and queue recipient emails."""
    if campaign.status == SourcingCampaign.Status.DRAFT:
        raise ValidationError({"status": "Only draft campaigns can be launched."})
    if not campaign.recipients.exists():
        raise ValidationError(
            {"recipients": "Add recipients (or attach a talent pool) before launching."}
        )
    campaign.status = SourcingCampaign.Status.ACTIVE
    campaign.started_at = timezone.now()
    campaign.updated_by = actor
    campaign.save(update_fields=["status", "started_at", "updated_at", "updated_by"])
    from apps.sources.tasks import send_campaign_emails

    send_campaign_emails.delay(str(campaign.pk))
    return campaign


@transaction.atomic
def pause_campaign(campaign: SourcingCampaign, *, actor=None) -> SourcingCampaign:
    if campaign.status != SourcingCampaign.Status.ACTIVE:
        raise ValidationError({"status": "Only active campaigns can be paused."})
    campaign.status = SourcingCampaign.Status.PAUSED
    campaign.updated_by = actor
    campaign.save(update_fields=["status", "updated_at", "updated_by"])
    return campaign


@transaction.atomic
def resume_campaign(campaign: SourcingCampaign, *, actor=None) -> SourcingCampaign:
    if campaign.status != SourcingCampaign.Status.PAUSED:
        raise ValidationError({"status": "Only paused campaigns can be resumed."})
    campaign.status = SourcingCampaign.Status.ACTIVE
    campaign.updated_by = actor
    campaign.save(update_fields=["status", "updated_at", "updated_by"])
    from apps.sources.tasks import send_campaign_emails

    send_campaign_emails.delay(str(campaign.pk))
    return campaign


@transaction.atomic
def complete_campaign(campaign: SourcingCampaign, *, actor=None) -> SourcingCampaign:
    if campaign.status not in (
        SourcingCampaign.Status.ACTIVE,
        SourcingCampaign.Status.PAUSED,
    ):
        raise ValidationError({"status": "Only active or paused campaigns can be completed."})
    campaign.status = SourcingCampaign.Status.COMPLETED
    campaign.ended_at = timezone.now()
    campaign.updated_by = actor
    campaign.save(update_fields=["status", "ended_at", "updated_at", "updated_by"])
    return campaign


@transaction.atomic
def add_recipients_from_pool(
    campaign: SourcingCampaign, *, actor=None
) -> list[CampaignRecipient]:
    """Create queued recipients from every member of the campaign's talent pool."""
    if not campaign.talent_pool_id:
        return []
    created = []
    for member in campaign.talent_pool.members.select_related("candidate"):
        if member.candidate and member.candidate.email:
            continue
        recipient, was_created = CampaignRecipient.objects.get_or_create(
            organization=campaign.organization,
            campaign=campaign,
            email=member.candidate.email,
            defaults={
                "candidate": member.candidate,
                "status": CampaignRecipient.Status.QUEUED,
                "created_by": actor,
                "updated_by": actor,
            },
        )
        if was_created:
            created.append(recipient)
    return created


# ---------------------------------------------------------------------------
# Recipient delivery
# ---------------------------------------------------------------------------


@transaction.atomic
def send_recipient_email(
    recipient: CampaignRecipient, *, actor=None, force: bool = False
) -> CampaignRecipient:
    """Deliver the campaign email to one recipient (mock SMTP behind a helper)."""
    if recipient.status not in (
        CampaignRecipient.Status.QUEUED,
        CampaignRecipient.Status.SENT,
    ) and not force:
        raise ValidationError(
            {"status": f"Cannot send recipient in status '{recipient.status}'."}
        )
    if recipient.status == CampaignRecipient.Status.OPTED_OUT:
        raise ValidationError({"status": "Recipient opted out."})

    _deliver_email(
        to=recipient.email,
        subject=f"Opportunity at {recipient.campaign.organization.name}",
        body=f"Hello{(' ' + recipient.candidate.full_name) if recipient.candidate else ''},\n\n"
        f"We thought you might be interested in an opportunity with "
        f"{recipient.campaign.organization.name}.\n\n"
        f"{recipient.campaign.goal or 'Learn more on our careers page.'}\n",
    )
    recipient.status = CampaignRecipient.Status.OPENED
    recipient.sent_at = timezone.now()
    recipient.updated_by = actor
    recipient.save(update_fields=["status", "sent_at", "updated_at", "updated_by"])
    return recipient


def _deliver_email(*, to: str, subject: str, body: str) -> None
    """
    Email transport seam. Currently logs the message; swap in a real
    SMTP/provider client here without touching callers.
    """
    logger.info("email to=%s subject=%r body=%r", to, subject, body[:200])


def campaign_recipients_for_send(campaign: SourcingCampaign):
    return CampaignRecipient.objects.filter(
        campaign=campaign,
        status=CampaignRecipient.Status.QUEUED,
        is_deleted=False,
    )


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


def attribution_stats(organization, *, date_from=None, date_to=None) -> dict:
    """Attributions aggregated by channel for the period."""
    now = timezone.now()
    if date_to is None:
        date_to = now.date()
    if date_from is None:
        date_from = date_to - timedelta(days=90)

    qs = CandidateSourceAttribution.objects.for_org(organization).filter(
        attribution_date__gte=date_from,
        attribution_date__lt=date_to,
        is_deleted=False,
    )
    by_channel = defaultdict(
        lambda: {"attributions": 0, "campaigns": set(), "channel_type": ""}
    )
    for attr in qs.select_related("channel", "campaign").only(
        "channel__name", "channel__channel_type", "campaign_id", "attribution_date"
    ):
        key = attr.channel.name
        by_channel[key]["attributions"] += 1
        by_channel[key]["channel_type"] = attr.channel.channel_type
        if attr.campaign_id:
            by_channel[key]["campaigns"].add(str(attr.campaign_id))

    rows = []
    for name, counts in sorted(by_channel.items(), key=lambda x: -x[1]["attributions"]):
        rows.append(
            {
                "channel": name,
                "channel_type": counts["channel_type"],
                "attributions": counts["attributions"],
                "campaigns": len(counts["campaigns"]),
            }
        )
    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "total_attributions": sum(r["attributions"] for r in rows),
        "channels": rows,
    }


def rollup_source_metrics(organization) -> dict:
    """Daily aggregation of sourcing activity (used by the beat task)."""
    today = timezone.now().date()
    return {
        "organization_id": str(organization.pk),
        "date": today.isoformat(),
        "channels": channel_stats(organization),
        "attributions": attribution_stats(organization, date_from=today, date_to=today),
    }
