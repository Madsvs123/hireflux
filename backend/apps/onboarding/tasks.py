"""
Celery tasks for onboarding reminders and offer-accepted plan creation.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_onboarding_reminders(self, plan_id: str | None = None):
    """Notify responsible users about due/overdue onboarding tasks."""
    from apps.onboarding.services import send_all_plan_reminders, send_plan_reminders

    try:
        if plan_id:
            from apps.onboarding.models import OnboardingPlan

            try:
                plan = OnboardingPlan.objects.select_related("candidate").get(pk=plan_id)
            except OnboardingPlan.DoesNotExist:
                logger.warning("send_onboarding_reminders: plan %s not found", plan_id)
                return {"ok": False, "error": "not_found"}
            count = send_plan_reminders(plan)
        else:
            count = send_all_plan_reminders()
        return {"ok": True, "reminded": count}
    except Exception as exc:
        logger.exception("send_onboarding_reminders failed")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=0, default_retry_delay=60)
def create_plan_from_offer(self, offer_id: str):
    """Auto-create an onboarding plan when an offer is accepted."""
    from apps.offers.models import Offer
    from apps.onboarding.services import create_plan_from_offer

    try:
        offer = Offer.objects.select_related("organization", "candidate").get(pk=offer_id)
    except Offer.DoesNotExist:
        logger.warning("create_plan_from_offer: offer %s not found", offer_id)
        return {"ok": False, "error": "not_found"}

    try:
        plan = create_plan_from_offer(offer)
        return {"ok": True, "plan_id": str(plan.pk), "status": plan.status}
    except Exception as exc:
        logger.exception("create_plan_from_offer failed for %s", offer_id)
        raise self.retry(exc=exc)
