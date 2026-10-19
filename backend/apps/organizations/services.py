"""
Organization provisioning services.
"""
import logging

from django.db import transaction

from apps.organizations.models import Organization

logger = logging.getLogger(__name__)


@transaction.atomic
def create_organization(
    *,
    name: str,
    org_type: str = Organization.OrgType.COMPANY,
    website: str = "",
    industry: str = "",
    size: str = "",
    slug: str | None = None,
    settings: dict | None = None,
    owner=None,
) -> Organization:
    """
    Create an organization and seed default roles + pipeline stages.
    """
    org = Organization(
        name=name,
        org_type=org_type,
        website=website or "",
        industry=industry or "",
        size=size or "",
        settings=settings or {},
    )
    if not slug:
        org.slug = slug
    org.save()

    # Seed default roles from accounts.Role
    try:
        from apps.accounts.models import Role

        Role.seed_defaults(org)
    except Exception:
        logger.exception("Failed to seed roles for org %s", org.pk)

    # Seed default pipeline via pipelines app when available
    try:
        from apps.pipelines.services import seed_default_pipeline

        seed_default_pipeline(org)
    except ImportError:
        logger.debug("pipelines.services.seed_default_pipeline not available yet")
    except Exception:
        logger.exception("Failed to seed pipeline for org %s", org.pk)

    if owner is not None:
        try:
            from apps.accounts.models import Membership, Role

            admin_role = Role.objects.filter(
                organization=org,
                slug="org-admin",
            ).first()
            Membership.objects.get_or_create(
                organization=org,
                user=owner,
                defaults={
                    "role": admin_role,
                    "is_owner": False,
                    "is_active": True,
                },
            )
        except Exception:
            logger.exception("Failed to attach owner membership for org %s", org.pk)

    return org
