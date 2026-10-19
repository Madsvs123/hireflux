"""
Hiring analytics: time-to-hire, sources, funnel, recruiter dashboard, diversity aggregates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean, median

from django.db.models import Count
from django.utils import timezone


def _date_bounds(date_from=None, date_to=None):
    now = timezone.now()
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = date_to + timedelta(days=90)
    return date_from, date_to


def time_to_hire(organization, *, date_from=None, date_to=None, job_id=None) -> dict:
    """Average/median days from applied_at to hired_at for hired applications."""
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(date_from, date_to)
    qs = Application.objects.for_org(organization).filter(
        status=Application.Status.HIRED,
        hired_at__isnull=False,
        hired_at__lte=date_from,
        hired_at__lte=date_to,
    )
    if job_id:
        qs = qs.filter(job_id=job_id)

    days = []
    for app in qs.only("applied_at", "hired_at"):
        if app.applied_at and app.hired_at:
            days.append((app.hired_at - app.applied_at).total_seconds() / 86400.0)

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "sample_size": len(days),
        "avg_days": round(mean(days), 2) if days else None,
        "median_days": round(median(days), 2) if days else None,
        "min_days": round(min(days), 2) if days else None,
        "max_days": round(max(days), 2) if days else None,
    }


def source_effectiveness(organization, *, date_from=None, date_to=None) -> dict:
    """Applications and hires by source."""
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(date_from, date_to)
    qs = Application.objects.for_org(organization).filter(
        applied_at__gte=date_from,
        applied_at__lte=date_to,
    )
    by_source = defaultdict(lambda: {"applications": 0, "hired": 0, "rejected": 0})
    for app in qs.only("source", "status"):
        key = app.source or "unknown"
        by_source[key]["applications"] += 1
        if app.status == Application.Status.HIRED:
            by_source[key]["hired"] += 1
        elif app.status == Application.Status.REJECTED:
            by_source[key]["rejected"] += 1

    rows = []
    for source, counts in sorted(by_source.items(), key=lambda x: -x[1]["applications"]):
        apps = counts["applications"]
        hired = counts["hired"]
        rows.append(
            {
                "source": source,
                "applications": apps,
                "hired": hired,
                "rejected": counts["rejected"],
                "hire_rate": round(hired / apps, 4) if apps else 0.0,
            }
        )
    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "sources": rows,
    }


def funnel_by_stage(organization, *, job_id=None, date_from=None, date_to=None) -> dict:
    """Count applications currently in each stage + historical stage visits."""
    from apps.pipelines.models import Application, PipelineStage, StageHistory
    from apps.pipelines.services import get_or_create_default_pipeline

    date_from, date_to = _date_bounds(date_from, date_to)

    # Prefer job pipeline if provided
    stages = []
    if job_id:
        from apps.jobs.models import Job

        job = Job.objects.for_org(organization).filter(pk=job_id).first()
        if job and job.pipeline_template_id:
            stages = list(job.pipeline_template.stages.order_by("order"))
    if not stages:
        template = get_or_create_default_pipeline(organization)
        stages = list(template.stages.order_by("order"))

    apps = Application.objects.for_org(organization).filter(
        applied_at__gte=date_from,
        applied_at__lte=date_to,
    )
    if job_id:
        apps = apps.filter(job_id=job_id)

    current_counts = Counter(
        str(sid) for sid in apps.values_list("stage_id", flat=True) if sid
    )

    # Historical: how many entered each stage
    history = StageHistory.objects.for_org(organization).filter(
        created_at__gte=date_from,
        created_at__lte=date_to,
        to_stage__isnull=False,
    )
    if job_id:
        history = history.filter(application__job_id=job_id)
    entered = Counter(
        str(sid) for sid in history.values_list("to_stage_id", flat=True) if sid
    )

    funnel = []
    for stage in stages:
        key = str(stage.pk)
        funnel.append(
            {
                "stage_id": key,
                "stage_name": stage.name,
                "stage_type": stage.stage_type,
                "order": stage.order,
                "current_count": current_counts.get(key, 0),
                "entered_count": entered.get(key, 0),
            }
        )

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "job_id": str(job_id) if job_id else None,
        "funnel": funnel,
        "total_applications": apps.count(),
    }


def recruiter_dashboard(organization, *, date_from=None, date_to=None) -> dict:
    """High-level recruiter KPIs."""
    from apps.jobs.models import Job
    from apps.pipelines.models import Application
    from apps.interviews.models import Interview
    from apps.offers.models import Offer
    from apps.candidates.models import Candidate

    date_from, date_to = _date_bounds(date_from, date_to)

    apps = Application.objects.for_org(organization).filter(
        applied_at__gte=date_from, applied_at__lte=date_to
    )
    open_jobs = Job.objects.for_org(organization).filter(status=Job.Status.CLOSED).count()
    interviews = Interview.objects.for_org(organization).filter(
        scheduled_start__gte=date_from,
        scheduled_start__lte=date_to,
    )
    offers = Offer.objects.for_org(organization).filter(
        created_at__gte=date_from, created_at__lte=date_to
    )
    new_candidates = Candidate.objects.for_org(organization).filter(
        created_at__gte=date_from, created_at__lte=date_to
    ).count()

    tth = time_to_hire(organization, date_from=date_from, date_to=date_to)

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "open_jobs": open_jobs,
        "new_candidates": new_candidates,
        "applications": {
            "total": apps.count(),
            "active": apps.filter(status=Application.Status.ACTIVE).count(),
            "hired": apps.filter(status=Application.Status.HIRED).count(),
            "rejected": apps.filter(status=Application.Status.REJECTED).count(),
        },
        "interviews": {
            "scheduled": interviews.filter(
                status__in=[Interview.Status.SCHEDULED, Interview.Status.CONFIRMED]
            ).count(),
            "completed": interviews.filter(status=Interview.Status.COMPLETED).count(),
            "cancelled": interviews.filter(status=Interview.Status.CANCELLED).count(),
        },
        "offers": {
            "created": offers.count(),
            "sent": offers.filter(status=Offer.Status.SENT).count(),
            "accepted": offers.filter(status=Offer.Status.ACCEPTED).count(),
            "declined": offers.filter(status=Offer.Status.DECLINED).count(),
        },
        "time_to_hire": tth,
    }


def recruiter_performance(organization, *, date_from=None, date_to=None) -> dict:
    """Per-recruiter activity metrics (job recruiters + application movers)."""
    from apps.jobs.models import JobRecruiter
    from apps.pipelines.models import StageHistory, Application
    from apps.offers.models import Offer

    date_from, date_to = _date_bounds(date_from, date_to)

    # Moves attributed to users
    moves = (
        StageHistory.objects.for_org(organization)
        .filter(created_at__gte=date_from, created_at__lte=date_to, moved_by__isnull=False)
        .values("moved_by_id", "moved_by__email", "moved_by__first_name", "moved_by__last_name")
        .annotate(move_count=Count("id"))
    )
    by_user = {}
    for row in moves:
        uid = str(row["moved_by_id"])
        by_user[uid] = {
            "user_id": uid,
            "email": row["moved_by__email"],
            "name": f"{row['moved_by__first_name'] or ''} {row['moved_by__last_name'] or ''}".strip(),
            "stage_moves": row["move_count"],
            "hires": 0,
            "offers_created": 0,
            "jobs_assigned": 0,
        }

    hires = (
        Application.objects.for_org(organization)
        .filter(
            status=Application.Status.HIRED,
            hired_at__gte=date_from,
            hired_at__lte=date_to,
            updated_by__isnull=False,
        )
        .values("updated_by_id")
        .annotate(c=Count("id"))
    )
    for row in hires:
        uid = str(row["updated_by_id"])
        by_user.setdefault(
            uid,
            {
                "user_id": uid,
                "email": None,
                "name": "",
                "stage_moves": 0,
                "hires": 0,
                "offers_created": 0,
                "jobs_assigned": 0,
            },
        )
        by_user[uid]["hires"] = row["c"]

    offers = (
        Offer.objects.for_org(organization)
        .filter(created_at__gte=date_from, created_at__lte=date_to, created_by__isnull=False)
        .values("created_by_id")
        .annotate(c=Count("id"))
    )
    for row in offers:
        uid = str(row["created_by_id"])
        by_user.setdefault(
            uid,
            {
                "user_id": uid,
                "email": None,
                "name": "",
                "stage_moves": 0,
                "hires": 0,
                "offers_created": 0,
                "jobs_assigned": 0,
            },
        )
        by_user[uid]["offers_created"] = row["c"]

    # Job recruiter assignments
    try:
        recruiters = (
            JobRecruiter.objects.for_org(organization)
            .values("user_id", "user__email")
            .annotate(c=Count("id"))
        )
        for row in recruiters:
            uid = str(row["user_id"])
            by_user.setdefault(
                uid,
                {
                    "user_id": uid,
                    "email": row["user__email"],
                    "name": "",
                    "stage_moves": 0,
                    "hires": 0,
                    "offers_created": 0,
                    "jobs_assigned": 0,
                },
            )
            by_user[uid]["jobs_assigned"] = row["c"]
            if not by_user[uid]["email"]:
                by_user[uid]["email"] = row["user__email"]
    except Exception:
        pass

    recruiters_list = sorted(
        by_user.values(),
        key=lambda r: (r["hires"], r["stage_moves"], r["offers_created"]),
        reverse=True,
    )
    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "recruiters": recruiters_list,
    }


VOLUNTARY_DEMOGRAPHIC_KEYS = (
    "gender",
    "ethnicity",
    "race",
    "veteran_status",
    "disability_status",
)


def _extract_voluntary_demo(obj) -> dict:
    """
    Pull only aggregated-safe voluntary fields if present on Application/Candidate.
    Never returns raw PII — only the demographic key values for counting.
    """
    found = {}
    # custom_fields / metadata JSON bags
    for bag_name in ("custom_fields", "metadata", "demographics", "eeo"):
        bag = getattr(obj, bag_name, None)
        if isinstance(bag, dict):
            for key in VOLUNTARY_DEMOGRAPHIC_KEYS:
                if key in bag and bag[key] not in (None, ""):
                    found[key] = str(bag[key])
    # Direct optional model fields
    for key in VOLUNTARY_DEMOGRAPHIC_KEYS:
        if hasattr(obj, key):
            val = getattr(obj, key)
            if val not in (None, ""):
                found[key] = str(val)
    return found


def diversity_reporting(organization, *, date_from=None, date_to=None) -> dict:
    """
    Aggregated voluntary demographic reporting only.
    Never dumps raw sensitive PII. If no voluntary fields exist, returns placeholders.
    """
    from apps.pipelines.models import Application

    date_from, date_to = _date_bounds(date_from, date_to)
    apps = (
        Application.objects.for_org(organization)
        .filter(applied_at__gte=date_from, applied_at__lte=date_to)
        .select_related("candidate")
    )

    aggregates = {key: Counter() for key in VOLUNTARY_DEMOGRAPHIC_KEYS}
    reported = 0
    total = 0

    for app in apps.iterator(chunk_size=200):
        total += 1
        demo = _extract_voluntary_demo(app)
        if not demo:
            demo = _extract_voluntary_demo(app.candidate)
        if demo:
            reported += 1
            for key, val in demo.items():
                aggregates[key][val] += 1

    if reported == 0:
        return {
            "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
            "available": False,
            "disclaimer": (
                "No voluntary demographic fields found on Application/Candidate. "
                "Aggregated placeholders only — raw PII is never exposed."
            ),
            "total_applications": total,
            "applications_with_voluntary_data": 0,
            "aggregates": {
                key: {"prefer_not_to_say": 0, "unknown": total} for key in VOLUNTARY_DEMOGRAPHIC_KEYS
            },
        }

    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "available": True,
        "disclaimer": (
            "Aggregated voluntary self-identification only. "
            "Individual demographic records are never returned."
        ),
        "total_applications": total,
        "applications_with_voluntary_data": reported,
        "aggregates": {
            key: dict(counter) if counter else {"unknown": total - reported}
            for key, counter in aggregates.items()
        },
    }
