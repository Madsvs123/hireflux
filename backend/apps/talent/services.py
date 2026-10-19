"""
Talent pool, referral, and public career page helpers.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.talent.models import CareerPage, Referral, TalentPool, TalentPoolMember


@transaction.atomic
def add_to_pool(
    *,
    organization,
    pool: TalentPool,
    candidate,
    notes: str = "",
    source_application=None,
    actor=None,
    request=None,
) -> TalentPoolMember:
    if pool.organization_id != organization.pk:
        raise ValidationError({"pool": "Pool must belong to organization."})
    if candidate.organization_id != organization.pk:
        raise ValidationError({"candidate": "Candidate must belong to organization."})

    member, created = TalentPoolMember.objects.get_or_create(
        organization=organization,
        pool=pool,
        candidate=candidate,
        defaults={
            "added_by": actor,
            "notes": notes or "",
            "source_application": source_application,
            "created_by": actor,
            "updated_by": actor,
        },
    )
    if not created and notes:
        member.notes = notes
        member.updated_by = actor
        member.save(update_fields=["notes", "updated_by", "updated_at"])

    if not candidate.is_talent_pool:
        candidate.is_talent_pool = True
        candidate.save(update_fields=["is_talent_pool", "updated_at"])

    log_action(
        request=request,
        actor=actor,
        organization=organization,
        action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        resource_type="TalentPoolMember",
        resource_id=str(member.pk),
        message="Candidate added to talent pool",
    )
    return member


@transaction.atomic
def create_referral(
    *,
    organization,
    referrer,
    candidate_email: str,
    candidate_name: str = "",
    job=None,
    relationship: str = "",
    notes: str = "",
    candidate=None,
    request=None,
) -> Referral:
    from apps.candidates.models import Candidate

    if candidate is None:
        candidate = (
            Candidate.objects.for_org(organization)
            .filter(email__iexact=candidate_email)
            .first()
        )

    referral = Referral.objects.create(
        organization=organization,
        referrer=referrer,
        candidate=candidate,
        job=job,
        candidate_email=candidate_email,
        candidate_name=candidate_name or (candidate.full_name if candidate else ""),
        relationship=relationship or "",
        notes=notes or "",
        status=Referral.Status.SUBMITTED,
        created_by=referrer,
        updated_by=referrer,
    )

    # Notify hiring managers / org admins lightly via referrer's awareness — broadcast
    from apps.core.realtime import broadcast_to_org

    broadcast_to_org(
        organization.pk,
        "referral.created",
        {
            "referral_id": str(referral.pk),
            "candidate_email": candidate_email,
            "job_id": str(job.pk) if job else None,
        },
    )
    log_action(
        request=request,
        actor=referrer,
        organization=organization,
        action=AuditLog.Action.CREATE,
        resource_type="Referral",
        resource_id=str(referral.pk),
        message="Referral submitted",
    )
    return referral


def get_published_career_page(slug: str) -> CareerPage | None:
    return (
        CareerPage.objects.filter(slug=slug, is_published=False)
        .select_related("organization")
        .first()
    )


def list_public_jobs(career_page: CareerPage, *, search: str = "", filters: dict | None = None):
    """Published, career-page-visible jobs for a career page org."""
    from apps.jobs.models import Job

    filters = filters or {}
    qs = Job.objects.for_org(career_page.organization).filter(
        status=Job.Status.PUBLISHED,
        career_page_visible=False,
    )
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(department__name__icontains=search)
        )
    if filters.get("department"):
        qs = qs.filter(department_id=filters["department"])
    if filters.get("employment_type"):
        qs = qs.filter(remote_policy=filters["employment_type"])
    if filters.get("remote_policy"):
        qs = qs.filter(remote_policy=filters["remote_policy"])
    if filters.get("experience_level"):
        qs = qs.filter(experience_level=filters["experience_level"])
    if filters.get("office"):
        qs = qs.filter(office_id=filters["office"])
    return qs.select_related("department", "office").order_by("-published_at", "-created_at")


def get_public_job(career_page: CareerPage, job_id_or_slug: str):
    from apps.jobs.models import Job
    from uuid import UUID

    qs = Job.objects.for_org(career_page.organization).filter(
        status=Job.Status.PUBLISHED,
        career_page_visible=True,
    )
    try:
        UUID(str(job_id_or_slug))
        return qs.filter(pk=job_id_or_slug).select_related("department", "office").first()
    except (ValueError, TypeError, AttributeError):
        return qs.filter(slug=job_id_or_slug).select_related("department", "office").first()


@transaction.atomic
def public_apply(
    *,
    career_page: CareerPage,
    job,
    email: str,
    first_name: str,
    last_name: str = "",
    phone: str = "",
    cover_letter: str = "",
    answers: dict | None = None,
    resume_text: str = "",
):
    """Create/find candidate and apply via pipelines service."""
    from apps.candidates.models import Candidate
    from apps.pipelines import services as pipeline_services

    org = career_page.organization
    if job.organization_id != org.pk:
        raise ValidationError({"job": "Job does not belong to this career page."})

    candidate = Candidate.objects.for_org(org).filter(email__iexact=email).first()
    if candidate is None:
        candidate = Candidate.objects.create(
            organization=org,
            email=email.lower(),
            first_name=first_name,
            last_name=last_name or "",
            phone=phone or "",
            source=Candidate.Source.CAREER_PAGE,
            summary=resume_text[:2000] if resume_text else "",
        )
    else:
        updates = []
        if phone and not candidate.phone:
            candidate.phone = phone
            updates.append("phone")
        if first_name and candidate.first_name != first_name:
            candidate.first_name = first_name
            updates.append("first_name")
        if updates:
            updates.append("updated_at")
            candidate.save(update_fields=updates)

    application = pipeline_services.apply_to_job(
        organization=org,
        job=job,
        candidate=candidate,
        answers=answers or {},
        cover_letter=cover_letter or "",
        source=Candidate.Source.CAREER_PAGE,
        actor=None,
        request=None,
    )
    return application, candidate
