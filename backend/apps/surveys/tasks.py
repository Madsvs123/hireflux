"""
Celery tasks for survey invitations, reminders, and analytics aggregation.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_survey_invitations(self, instance_id: str):
    """Deliver invitation emails for a survey instance."""
    from apps.surveys.models import SurveyInstance, SurveyInvitation
    from apps.surveys.services import _deliver_email

    try:
        instance = SurveyInstance.objects.select_related("template").get(pk=instance_id)
    except SurveyInstance.DoesNotExist:
        logger.warning("send_survey_invitations: instance %s not found", instance_id)
        return {"ok": False, "error": "not_found"}

    sent = 0
    last_sent_at = None
    invitations = instance.invitations.filter(
        status__in=[SurveyInvitation.Status.SENT, SurveyInvitation.Status.OPENED], is_deleted=False
    )
    for invitation in invitations.iterator():
        _deliver_email(
            to=invitation.email,
            subject=f"Tell us about your experience — {instance.template.name}",
            body=(
                f"Hi,\n\nPlease take a moment to complete our survey "
                f"'{instance.template.name}'.\n\n"
                f"https://example.com/public/surveys/{instance.token}/\n"
            ),
        )
        invitation.status = SurveyInvitation.Status.SENT
        invitation.sent_at = timezone.now()
        invitation.save(update_fields=["status", "sent_at", "updated_at"])
        last_sent_at = invitation.sent_at
        sent += 1

    if instance.status == SurveyInstance.Status.DRAFT:
        instance.status = SurveyInstance.Status.SENT
        instance.sent_at = last_sent_at or timezone.now()
        instance.save(update_fields=["status", "sent_at", "updated_at"])

    return {"ok": True, "instance_id": instance_id, "sent": sent}


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_survey_reminders(self, instance_id: str):
    """Send a reminder wave to pending invitations."""
    from apps.surveys.models import SurveyInstance, SurveyInvitation
    from apps.surveys.services import _deliver_email

    try:
        instance = SurveyInstance.objects.select_related("template").get(pk=instance_id)
    except SurveyInstance.DoesNotExist:
        logger.warning("send_survey_reminders: instance %s not found", instance_id)
        return {"ok": False, "error": "not_found"}

    invitations = instance.invitations.filter(
        status__in=[
            SurveyInvitation.Status.QUEUED,
            SurveyInvitation.Status.SENT,
            SurveyInvitation.Status.OPENED,
        ],
        is_deleted=False,
    )
    reminded = 0
    for invitation in invitations.iterator():
        _deliver_email(
            to=invitation.email,
            subject=f"Reminder: {instance.template.name}",
            body=(
                f"Hi,\n\nJust a reminder to complete our survey "
                f"'{instance.template.name}' if you haven't yet.\n\n"
                f"https://example.com/public/surveys/{instance.token}/\n"
            ),
        )
        invitation.status = SurveyInvitation.Status.SENT
        invitation.sent_at = timezone.now()
        invitation.save(update_fields=["status", "sent_at", "updated_at"])
        reminded += 1

    return {"ok": True, "instance_id": instance_id, "reminded": reminded}


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def aggregate_survey_analytics(self, template_id: str):
    """Compute and log survey analytics for a template (cache-friendly)."""
    from apps.surveys.models import SurveyTemplate
    from apps.surveys.services import survey_analytics

    try:
        template = SurveyTemplate.objects.get(pk=template_id)
    except SurveyTemplate.DoesNotExist:
        logger.warning("aggregate_survey_analytics: template %s not found", template_id)
        return {"ok": False, "error": "not_found"}
    try:
        analytics = survey_analytics(template)
        return {"ok": True, **analytics}
    except Exception as exc:  # noqa: BLE001
        logger.exception("aggregate_survey_analytics failed for %s", template_id)
        raise self.retry(exc=exc)
