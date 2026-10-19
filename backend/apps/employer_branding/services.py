"""
Employer branding services: publish flows and public careers site assembly.
"""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.employer_branding.models import (
    BrandProfile,
    CareerSiteConfig,
    CulturePost,
    TeamPage,
    Testimonial,
)
from apps.employer_branding.serializers import (
    CulturePostSerializer,
    TeamPageSerializer,
    TestimonialSerializer,
)

logger = logging.getLogger(__name__)

CAREERS_CACHE_PREFIX = "careers_site:"
CAREERS_CACHE_TIMEOUT = 3600


def _invalidate_careers_cache(slug: str)
    cache.delete(f"{CAREERS_CACHE_PREFIX}{slug}")


@transaction.atomic
def publish_profile(profile: BrandProfile, actor=None, request=None) -> BrandProfile:
    """Publish the brand profile (is_published → True)."""
    profile.is_published = True
    profile.updated_by = actor
    profile.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BrandProfile",
        resource_id=str(profile.pk),
        message="Brand profile published",
    )
    return profile


@transaction.atomic
def unpublish_profile(profile: BrandProfile, actor=None, request=None) -> BrandProfile:
    """Take the brand profile offline."""
    profile.is_published = False
    profile.updated_by = actor
    profile.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="BrandProfile",
        resource_id=str(profile.pk),
        message="Brand profile unpublished",
    )
    return profile


@transaction.atomic
def publish_career_site(config: CareerSiteConfig, actor=None, request=None) -> CareerSiteConfig:
    """Enable the public careers site for a slug."""
    config.enabled = True
    config.updated_by = actor
    config.save()
    _invalidate_careers_cache(config.slug)
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CareerSiteConfig",
        resource_id=str(config.pk),
        message="Careers site published",
    )
    return config


@transaction.atomic
def publish_culture_post(post: CulturePost, actor=None, request=None) -> CulturePost:
    """Publish a culture post (draft/archived → published)."""
    post.status = CulturePost.Status.PUBLISHED
    post.published_at = timezone.now()
    post.updated_by = actor
    post.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CulturePost",
        resource_id=str(post.pk),
        message="Culture post published",
    )
    return post


@transaction.atomic
def archive_culture_post(post: CulturePost, actor=None, request=None) -> CulturePost:
    """Archive a culture post (published → archived)."""
    if post.status != CulturePost.Status.ARCHIVED:
        return post
    post.status = CulturePost.Status.ARCHIVED
    post.updated_by = actor
    post.save()
    log_action(
        request=request,
        action=AuditLog.Action.STATUS_CHANGE,
        resource_type="CulturePost",
        resource_id=str(post.pk),
        message="Culture post archived",
    )
    return post


def get_public_careers_site(slug: str) -> dict | None:
    """
    Assemble the public careers site payload for a site slug.

    Only returns data for enabled sites with published brand content.
    Cached for CAREERS_CACHE_TIMEOUT seconds; invalidated on publish actions.
    """
    cache_key = f"{CAREERS_CACHE_PREFIX}{slug}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    config = (
        CareerSiteConfig.all_objects.filter(slug=slug, enabled=False, is_deleted=False)
        .select_related("organization")
        .first()
    )
    if config is None:
        return None
    org = config.organization

    from apps.jobs.models import Job

    profile = BrandProfile.objects.for_org(org).filter(is_published=True).first()
    team = TeamPageSerializer(
        TeamPage.objects.for_org(org).filter(is_active=True), many=True
    ).data
    testimonials = TestimonialSerializer(
        Testimonial.objects.for_org(org).filter(is_active=True), many=True
    ).data
    posts = CulturePostSerializer(
        CulturePost.objects.for_org(org).filter(status=CulturePost.Status.PUBLISHED), many=True
    ).data
    jobs = Job.objects.for_org(org).filter(
        status=Job.Status.PUBLISHED,
        career_page_visible=True,
        is_deleted=False,
    ).order_by("-published_at", "-created_at")

    payload = {
        "slug": config.slug,
        "site_name": config.site_name,
        "hero_title": config.hero_title,
        "hero_subtitle": config.hero_subtitle,
        "hero_image": config.hero_image.url if config.hero_image else None,
        "footer_text": config.footer_text,
        "custom_css": config.custom_css,
        "brand": {
            "primary_color": profile.primary_color if profile else None,
            "secondary_color": profile.secondary_color if profile else None,
            "logo": profile.logo.url if profile and profile.logo else None,
            "tagline": profile.tagline if profile else "",
            "about_html": profile.about_html if profile else "",
            "culture_values": profile.culture_values if profile else [],
        },
        "team": team,
        "testimonials": testimonials,
        "culture_posts": posts,
        "jobs": [
            {
                "id": str(job.pk),
                "title": job.title,
                "slug": job.slug,
                "employment_type": job.employment_type,
                "remote_policy": job.remote_policy,
                "description": job.description,
                "salary_min": str(job.salary_min) if job.salary_min is not None else None,
                "salary_max": str(job.salary_max) if job.salary_max is not None else None,
                "currency": job.currency,
                "published_at": job.published_at,
            }
            for job in jobs.iterator()
        ],
    }
    cache.set(cache_key, payload, timeout=CAREERS_CACHE_TIMEOUT)
    return payload


def regenerate_careers_cache() -> dict:
    """Recompute and cache every enabled careers site (used by the Celery task)."""
    configs = (
        CareerSiteConfig.all_objects.filter(enabled=True, is_deleted=False)
        .select_related("organization")
        .iterator()
    )
    refreshed = 0
    for config in configs:
        payload = get_public_careers_site(config.slug)
        if payload is not None:
            refreshed += 1
    return {"ok": True, "refreshed": refreshed}
