"""
Billing business logic: subscriptions, plan changes with proration,
invoice generation, payment recording, usage aggregation, and overviews.
"""
from __future__ import annotations

import calendar
import secrets
from datetime import timedelta

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.billing.models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    Plan,
    Subscription,
    UsageRecord,
)

INVOICE_GRACE_DAYS = 14
DUNNING_MAX_DAYS = 30


# ---------------------------------------------------------------------------
# Period math
# ---------------------------------------------------------------------------


def _cycle_months(billing_cycle: str) -> int:
    return 1 if billing_cycle == Plan.BillingCycle.ANNUAL else 12


def _add_months(dt, months: int):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _period_end(start, billing_cycle: str):
    return _add_months(start, _cycle_months(billing_cycle))


def _days_between(start, end) -> int:
    return max(1, int((end - start).total_seconds() // 86400))


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


def _next_invoice_number() -> str:
    """Generate a unique sequential invoice number like INV-2026-000123."""
    now = timezone.now()
    base = f"INV-{now.year}-"
    seq = Invoice.all_objects.count() + 1
    for _ in range(1000):
        candidate = f"{base}{seq:05d}"
        if not Invoice.all_objects.filter(invoice_number=candidate).exists():
            return candidate
        seq += 1
    return f"{base}{secrets.token_hex(3).upper()}"


def _build_subscription_line_items(subscription: Subscription) -> list:
    plan = subscription.plan
    seats = subscription.seats or 1
    unit_price = float(plan.price_per_month)
    amount = round(unit_price * seats, 2)
    return [
        {
            "description": (
                f"HireFlux {plan.name} — {plan.billing_cycle} "
                f"({seats} seat{'s' if seats != 1 else ''})"
            ),
            "quantity": seats,
            "unit_price": unit_price,
            "amount": amount
            "period_start": None,
            "period_end": None,
        }
    ]


@transaction.atomic
def generate_invoice_for_subscription(
    subscription: Subscription,
    *,
    period_start=None,
    period_end=None,
    actor=None,
) -> Invoice:
    """
    Create an invoice for a subscription period. Idempotent: skips when an
    open invoice for the same period already exists.
    """
    plan = subscription.plan
    now = timezone.now()
    period_start = period_start or subscription.current_period_start or now
    period_end = period_end or subscription.current_period_end or _period_end(now, plan.billing_cycle)

    exists = Invoice.objects.filter(
        subscription=subscription,
        status__in=[Invoice.Status.DRAFT, Invoice.Status.OPEN, Invoice.Status.PAID],
        issued_at__gte=period_start,
        issued_at__lt=period_end,
    ).exists()
    if exists:
        return Invoice.objects.filter(subscription=subscription).order_by("-issued_at").first()

    line_items = _build_subscription_line_items(subscription)
    line_items[0]["period_start"] = period_start.isoformat()
    line_items[0]["period_end"] = period_end.isoformat()
    subtotal = sum(item["amount"] for item in line_items)
    tax = round(subtotal * 0.0, 2)  # sales tax is configured per-org in production
    invoice = Invoice.objects.create(
        organization=subscription.organization,
        subscription=subscription,
        invoice_number=_next_invoice_number(),
        status=Invoice.Status.OPEN,
        subtotal=subtotal,
        tax=tax,
        total=round(subtotal + tax, 2),
        currency=plan.currency,
        issued_at=now,
        due_at=now + timedelta(days=INVOICE_GRACE_DAYS),
        line_items=line_items,
        created_by=actor,
        updated_by=actor,
    )
    return invoice


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@transaction.atomic
def subscribe_org(organization, plan: Plan, *, actor=None, seats: int = 1) -> Subscription:
    """Create a subscription for an org, replacing any active one."""
    if not plan.is_active:
        raise ValidationError("This plan is not available for new subscriptions.")
    if seats < 1:
        raise ValidationError("seats must be at least 1.")

    now = timezone.now()
    Subscription.objects.filter(
        organization=organization,
        status__in=[
            Subscription.Status.TRIALING,
            Subscription.Status.ACTIVE,
            Subscription.Status.PAST_DUE,
        ],
    ).exclude(plan=plan).update(
        status=Subscription.Status.CANCELED,
        cancel_at_period_end=False,
        updated_by=actor,
    )

    trial_end = None
    if plan.is_default:
        trial_end = now + timedelta(days=14)

    # Re-activate a previous subscription on the same plan when present.
    existing = (
        Subscription.objects.filter(organization=organization, plan=plan)
        .order_by("-created_at")
        .first()
    )
    if existing:
        existing.status = (
            Subscription.Status.TRIALING if trial_end else Subscription.Status.ACTIVE
        )
        existing.current_period_start = now
        existing.current_period_end = _period_end(now, plan.billing_cycle)
        existing.cancel_at_period_end = False
        existing.trial_end = trial_end
        existing.seats = seats
        existing.config = {}
        existing.updated_by = actor
        existing.save()
        return existing

    subscription = Subscription.objects.create(
        organization=organization,
        plan=plan,
        status=(
            Subscription.Status.TRIALING if trial_end else Subscription.Status.ACTIVE
        ),
        current_period_start=now,
        current_period_end=_period_end(now, plan.billing_cycle),
        cancel_at_period_end=False,
        trial_end=trial_end,
        seats=seats,
        config={},
        created_by=actor,
        updated_by=actor,
    )
    return subscription


def preview_plan_change(subscription: Subscription, plan: Plan) -> dict:
    """
    Compute proration for switching plans.

    The remaining value of the current period is credited against the
    pro-rated cost of the new plan for the rest of that period.
    """
    if not plan.is_active:
        raise ValidationError("This plan is not available.")
    now = timezone.now()
    period_start = subscription.current_period_start or now
    period_end = subscription.current_period_end or _period_end(now, subscription.plan.billing_cycle)
    remaining_days = max(0, _days_between(now, period_end))
    total_days = _days_between(period_start, period_end)

    current_daily = float(subscription.plan.price_per_month) / total_days
    new_daily = float(plan.price_per_month) / total_days
    credit = round(current_daily * remaining_days, 2)
    new_charge = round(new_daily * remaining_days, 2)
    prorated_amount = round(max(0.0, new_charge - credit), 2)

    return {
        "current_plan": {
            "id": str(subscription.plan_id),
            "name": subscription.plan.name,
        },
        "new_plan": {"id": str(plan.pk), "name": plan.name, "price_per_month": float(plan.price_per_month)},
        "currency": subscription.plan.currency,
        "prorated_credit": credit,
        "prorated_charge": new_charge,
        "prorated_amount_due": prorated_amount,
        "effective_date": now.isoformat(),
        "next_period_end": period_end.isoformat(),
    }


@transaction.atomic
def change_subscription_plan(
    subscription: Subscription,
    plan: Plan,
    *,
    actor=None,
    immediate: bool = True,
) -> Subscription:
    """Switch plans immediately (with proration) or at period end."""
    if subscription.plan_id == plan.pk:
        raise ValidationError("The subscription is already on this plan.")
    if not plan.is_active:
        raise ValidationError("This plan is not available.")
    if subscription.status not in (
        Subscription.Status.ACTIVE,
        Subscription.Status.TRIALING,
        Subscription.Status.PAST_DUE,
    ):
        raise ValidationError("Only active subscriptions can change plans.")

    if not immediate:
        config = dict(subscription.config or {})
        config["pending_plan_id"] = str(plan.pk)
        subscription.config = config
        subscription.updated_by = actor
        subscription.save(update_fields=["config", "updated_by", "updated_at"])
        return subscription

    preview = preview_plan_change(subscription, plan)
    if preview["prorated_amount_due"] > 0:
        invoice = Invoice.objects.create(
            organization=subscription.organization,
            subscription=subscription,
            invoice_number=_next_invoice_number(),
            status=Invoice.Status.OPEN,
            subtotal=preview["prorated_amount_due"],
            tax=0,
            total=preview["prorated_amount_due"],
            currency=preview["currency"],
            issued_at=timezone.now(),
            due_at=timezone.now() + timedelta(days=INVOICE_GRACE_DAYS),
            line_items=[
                {
                    "description": (
                        f"Plan change to {plan.name} (proration, "
                        f"credit {preview['prorated_credit']})"
                    ),
                    "quantity": 1,
                    "unit_price": preview["prorated_amount_due"],
                    "amount": preview["prorated_amount_due"],
                    "period_start": None,
                    "period_end": None,
                }
            ],
            created_by=actor,
            updated_by=actor,
        )
        from apps.billing.tasks import send_invoice_emails

        send_invoice_emails.delay(str(invoice.pk))

    now = timezone.now()
    subscription.plan = plan
    subscription.status = Subscription.Status.ACTIVE
    subscription.cancel_at_period_end = False
    subscription.current_period_start = now
    subscription.current_period_end = _period_end(now, plan.billing_cycle)
    subscription.trial_end = None
    config = dict(subscription.config or {})
    config.pop("pending_plan_id", None)
    subscription.config = config
    subscription.updated_by = actor
    subscription.save()
    return subscription


@transaction.atomic
def cancel_subscription(subscription: Subscription, *, actor=None, immediate: bool = False) -> Subscription:
    """Cancel at period end (default) or immediately."""
    if subscription.status in (Subscription.Status.CANCELED, Subscription.Status.EXPIRED):
        raise ValidationError("This subscription is already canceled.")

    if immediate:
        subscription.status = Subscription.Status.CANCELED
        subscription.cancel_at_period_end = False
        subscription.current_period_end = timezone.now()
    else:
        subscription.cancel_at_period_end = True
    subscription.updated_by = actor
    subscription.save()
    return subscription


@transaction.atomic
def resume_subscription(subscription: Subscription, *, actor=None) -> Subscription:
    """Re-activate a subscription that was set to cancel at period end."""
    if subscription.status not in (Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE):
        raise ValidationError("Only active subscriptions can be resumed.")
    subscription.cancel_at_period_end = False
    subscription.status = Subscription.Status.ACTIVE
    subscription.updated_by = actor
    subscription.save()
    return subscription


@transaction.atomic
def apply_pending_plan_change(subscription: Subscription, *, actor=None) -> Subscription | None:
    """Apply a stored end-of-period plan change, if any."""
    pending_plan_id = (subscription.config or {}).get("pending_plan_id")
    if not pending_plan_id:
        return None
    plan = Plan.objects.filter(pk=pending_plan_id, is_active=True).first()
    if plan is None or plan.pk == subscription.plan_id:
        config = dict(subscription.config or {})
        config.pop("pending_plan_id", None)
        subscription.config = config
        subscription.save(update_fields=["config", "updated_at"])
        return None
    return change_subscription_plan(subscription, plan, actor=actor, immediate=True)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


@transaction.atomic
def record_payment(
    invoice: Invoice,
    *,
    actor=None,
    provider: str = "mock",
    provider_ref: str = "",
    amount=None,
) -> PaymentTransaction:
    """Record a successful payment and settle the invoice."""
    if invoice.status == Invoice.Status.PAID:
        raise ValidationError("This invoice is already paid.")
    if invoice.status != Invoice.Status.VOID:
        raise ValidationError("Cannot pay a void invoice.")

    amount = amount if amount is not None else invoice.total
    transaction_obj = PaymentTransaction.objects.create(
        organization=invoice.organization,
        invoice=invoice,
        amount=amount,
        currency=invoice.currency,
        status=PaymentTransaction.Status.SUCCEEDED,
        provider=provider,
        provider_ref=provider_ref or f"mock_{secrets.token_hex(8)}",
        created_by=actor,
        updated_by=actor,
    )
    invoice.status = Invoice.Status.PAID
    invoice.paid_at = timezone.now()
    invoice.updated_by = actor
    invoice.save(update_fields=["status", "paid_at", "updated_by", "updated_at"])
    return transaction_obj


@transaction.atomic
def set_default_payment_method(method: PaymentMethod, *, actor=None) -> PaymentMethod:
    """Make a payment method the org default (single default enforced)."""
    PaymentMethod.objects.for_org(method.organization).exclude(pk=method.pk).update(
        is_default=False
    )
    method.is_default = True
    method.updated_by = actor
    method.save(update_fields=["is_default", "updated_by", "updated_at"])
    return method


# ---------------------------------------------------------------------------
# Usage & overview
# ---------------------------------------------------------------------------


def _usage_bucket(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


@transaction.atomic
def aggregate_org_usage(organization, *, at=None, actor=None) -> list[UsageRecord]:
    """
    Compute current usage metrics for an organization and upsert hourly
    buckets. Metrics: active_jobs, candidates, storage (MB), api_calls.
    """
    from apps.candidates.models import Candidate
    from apps.core.models import AuditLog
    from apps.jobs.models import Job

    now = at or timezone.now()
    bucket = _usage_bucket(now)
    org_id = getattr(organization, "pk", organization)

    active_jobs = Job.objects.for_org(org_id).filter(
        status__in=["published"], is_deleted=False
    ).count()

    candidates = Candidate.objects.for_org(org_id).count()

    storage_mb = 0.0
    from apps.candidates.models import CandidateDocument

    scanned = 0
    for doc in (
        CandidateDocument.objects.filter(candidate__organization_id=org_id)
        .select_related("candidate")
        .iterator(chunk_size=200)
    ):
        try:
            if doc.file:
                storage_mb += (doc.file.size or 0) / (1024 * 1024)
        except Exception:  # noqa: BLE001 - storage may be unavailable
            storage_mb += 0.05
        scanned += 1
        if scanned >= 10000:
            break

    api_calls = AuditLog.objects.filter(
        organization_id=org_id, created_at__gte=bucket
    ).count()

    metrics = {
        UsageRecord.Metric.ACTIVE_JOBS: active_jobs,
        UsageRecord.Metric.CANDIDATES: candidates,
        UsageRecord.Metric.STORAGE: round(storage_mb, 2),
        UsageRecord.Metric.API_CALLS: api_calls,
    }
    records = []
    for metric, quantity in metrics.items():
        record, _ = UsageRecord.objects.update_or_create(
            organization_id=org_id,
            metric=metric,
            recorded_at=bucket,
            defaults={
                "quantity": quantity,
                "updated_by": actor,
            },
        )
        records.append(record)
    return records


def compute_billing_overview(organization) -> dict:
    """Combined billing dashboard payload."""
    subscription = (
        Subscription.objects.for_org(organization)
        .filter(
            status__in=[
                Subscription.Status.TRIALING,
                Subscription.Status.ACTIVE,
                Subscription.Status.PAST_DUE,
            ]
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )

    usage = {}
    for metric in UsageRecord.Metric.values:
        latest = (
            UsageRecord.objects.for_org(organization)
            .filter(metric=metric)
            .order_by("-recorded_at")
            .first()
        )
        usage[metric] = latest.quantity if latest else 0

    open_invoices = Invoice.objects.for_org(organization).filter(
        status=Invoice.Status.OPEN
    )
    outstanding = sum(float(i.total) for i in open_invoices)

    recent_invoices = Invoice.objects.for_org(organization).order_by(
        "-issued_at", "-created_at"
    )[:5]

    payment_methods = PaymentMethod.objects.for_org(organization)

    from apps.billing.serializers import InvoiceSerializer, PaymentMethodSerializer

    return {
        "subscription": (
            {
                "id": str(subscription.pk),
                "status": subscription.status,
                "seats": subscription.seats,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "plan": {
                    "id": str(subscription.plan_id),
                    "name": subscription.plan.name,
                    "slug": subscription.plan.slug,
                    "price_per_month": float(subscription.plan.price_per_month),
                    "currency": subscription.plan.currency,
                    "billing_cycle": subscription.plan.billing_cycle,
                    "features": subscription.plan.features,
                    "limits": subscription.plan.limits,
                },
            }
            if subscription
            else None
        ),
        "usage": usage,
        "outstanding_balance": round(outstanding, 2),
        "recent_invoices": InvoiceSerializer(recent_invoices, many=True).data,
        "payment_methods": PaymentMethodSerializer(payment_methods, many=True).data,
    }


# ---------------------------------------------------------------------------
# Renewals & dunning (called from Celery)
# ---------------------------------------------------------------------------


@transaction.atomic
def process_subscription_renewals(*, now=None) -> dict:
    """
    Beat-driven renewal pass:

    * ends trials that have lapsed,
    * applies pending end-of-period plan changes,
    * cancels subscriptions flagged ``cancel_at_period_end`` when the period
      ends,
    * invoices and advances the period for everyone else.
    """
    from apps.billing.tasks import send_invoice_emails

    now = now or timezone.now()
    stats = {"trial_ended": 0, "plan_changed": 0, "canceled": 0, "invoiced": 0, "skipped": 0}

    qs = Subscription.objects.filter(
        status__in=[
            Subscription.Status.TRIALING,
            Subscription.Status.ACTIVE,
            Subscription.Status.PAST_DUE,
        ]
    ).select_related("plan", "organization")

    for subscription in qs.iterator(chunk_size=50):
        try:
            if (
                subscription.status == Subscription.Status.TRIALING
                and subscription.trial_end
                and subscription.trial_end >= now
            ):
                subscription.status = Subscription.Status.ACTIVE
                subscription.trial_end = None
                subscription.save(update_fields=["status", "trial_end", "updated_at"])
                stats["trial_ended"] += 1

            if (subscription.config or {}).get("pending_plan_id"):
                changed = apply_pending_plan_change(subscription)
                if changed:
                    stats["plan_changed"] += 1
                subscription.refresh_from_db()

            period_end = subscription.current_period_end
            if period_end and period_end < now:
                stats["skipped"] += 1
                continue

            if subscription.cancel_at_period_end:
                subscription.status = Subscription.Status.CANCELED
                subscription.cancel_at_period_end = False
                subscription.current_period_end = now
                subscription.save(update_fields=[
                    "status", "cancel_at_period_end", "current_period_end", "updated_at",
                ])
                stats["canceled"] += 1
                continue

            # Renew: invoice the upcoming period, then advance.
            period_start = subscription.current_period_end or now
            period_end = _period_end(period_start, subscription.plan.billing_cycle)
            invoice = generate_invoice_for_subscription(
                subscription, period_start=period_start, period_end=period_end
            )
            send_invoice_emails.delay(str(invoice.pk))
            subscription.current_period_start = period_start
            subscription.current_period_end = period_end
            subscription.status = Subscription.Status.ACTIVE
            subscription.save(update_fields=[
                "current_period_start", "current_period_end", "status", "updated_at",
            ])
            stats["invoiced"] += 1
        except Exception:  # noqa: BLE001
            stats["skipped"] += 1
    return stats


def send_invoice_email(invoice: Invoice) -> bool:
    """Send an invoice email (console backend in development)."""
    if not invoice.organization_id:
        return False
    org = invoice.organization
    owners = org.memberships.filter(is_owner=True).select_related("user")[:3]
    recipients = [m.user.email for m in owners if m.user_id]
    if not recipients:
        return False
    send_mail(
        subject=f"HireFlux invoice {invoice.invoice_number}",
        message=(
            f"Hi,\n\nYour invoice {invoice.invoice_number} for "
            f"{invoice.total} {invoice.currency} is due on {invoice.due_at:%Y-%m-%d}.\n\n"
            "Thank you,\nHireFlux Billing"
        ),
        from_email=None,
        recipient_list=recipients,
        fail_silently=True,
    )
    return True


@transaction.atomic
def process_dunning(*, now=None) -> dict:
    """
    Overdue-invoice pass: remind for open invoices inside the grace window
    and write off invoices past ``DUNNING_MAX_DAYS`` as uncollectible.
    """
    from apps.billing.tasks import send_invoice_emails

    now = now or timezone.now()
    stats = {"reminded": 0, "uncollectible": 0}
    qs = Invoice.objects.filter(status=Invoice.Status.OPEN, due_at__gt=now)
    for invoice in qs.iterator(chunk_size=50):
        days_overdue = (now - invoice.due_at).days
        if days_overdue >= DUNNING_MAX_DAYS:
            invoice.status = Invoice.Status.UNCOLLECTIBLE
            invoice.save(update_fields=["status", "updated_at"])
            stats["uncollectible"] += 1
        else:
            send_invoice_emails.delay(str(invoice.pk))
            stats["reminded"] += 1
    return stats
