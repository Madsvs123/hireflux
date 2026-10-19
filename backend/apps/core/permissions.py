"""
ATS permission catalog, personas, and DRF permission classes.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

# ---------------------------------------------------------------------------
# Permission catalog — dotted codes used in Role.permissions JSON
# ---------------------------------------------------------------------------
PERMISSION_CATALOG = {
    "org": {
        "org.view": "View organization settings",
        "org.edit": "Edit organization settings",
        "org.billing": "Manage billing",
        "org.delete": "Delete organization",
    },
    "users": {
        "users.view": "View members",
        "users.invite": "Invite members",
        "users.edit": "Edit members",
        "users.remove": "Remove members",
        "users.roles": "Manage roles",
    },
    "jobs": {
        "jobs.view": "View jobs",
        "jobs.create": "Create jobs",
        "jobs.edit": "Edit jobs",
        "jobs.publish": "Publish jobs",
        "jobs.close": "Close jobs",
        "jobs.delete": "Delete jobs",
    },
    "candidates": {
        "candidates.view": "View candidates",
        "candidates.create": "Create candidates",
        "candidates.edit": "Edit candidates",
        "candidates.delete": "Delete candidates",
        "candidates.export": "Export candidates",
        "candidates.merge": "Merge candidates",
    },
    "pipelines": {
        "pipelines.view": "View pipelines",
        "pipelines.edit": "Edit pipelines",
        "pipelines.move": "Move candidates in pipeline",
    },
    "screening": {
        "screening.view": "View screening",
        "screening.manage": "Manage screening questions",
        "screening.score": "Score screening responses",
    },
    "interviews": {
        "interviews.view": "View interviews",
        "interviews.schedule": "Schedule interviews",
        "interviews.feedback": "Submit interview feedback",
        "interviews.manage": "Manage interview kits",
    },
    "assessments": {
        "assessments.view": "View assessments",
        "assessments.create": "Create assessments",
        "assessments.score": "Score assessments",
        "assessments.manage": "Manage assessment templates",
    },
    "offers": {
        "offers.view": "View offers",
        "offers.create": "Create offers",
        "offers.approve": "Approve offers",
        "offers.send": "Send offers",
    },
    "talent": {
        "talent.view": "View talent pools",
        "talent.manage": "Manage talent pools",
        "talent.sourcers": "Manage agency sourcers",
    },
    "career": {
        "career.view": "View career page",
        "career.edit": "Edit career page",
    },
    "comms": {
        "comms.view": "View messages",
        "comms.send": "Send messages",
        "comms.templates": "Manage email templates",
    },
    "portal": {
        "portal.view": "View candidate portal settings",
        "portal.manage": "Manage candidate portal",
    },
    "audit": {
        "audit.view": "View audit log",
    },
    "analytics": {
        "analytics.view": "View analytics",
        "analytics.export": "Export analytics",
    },
}


def all_permission_codes():
    codes = []
    for group in PERMISSION_CATALOG.values():
        codes.extend(group.keys())
    return codes


# ---------------------------------------------------------------------------
# Staff personas with default permission sets
# ---------------------------------------------------------------------------
STAFF_PERSONAS = {
    "org_admin": {
        "label": "Organization Admin",
        "description": "Full access to organization settings and hiring operations",
        "permissions": None,  # filled below
    },
    "hiring_manager": {
        "label": "Hiring Manager",
        "description": "Owns requisitions, interviews, and hiring decisions",
        "permissions": [
            "org.view",
            "users.view",
            "jobs.view",
            "jobs.create",
            "jobs.edit",
            "jobs.publish",
            "jobs.close",
            "candidates.view",
            "candidates.create",
            "candidates.edit",
            "pipelines.view",
            "pipelines.move",
            "screening.view",
            "screening.score",
            "interviews.view",
            "interviews.schedule",
            "interviews.feedback",
            "assessments.view",
            "assessments.score",
            "offers.view",
            "offers.create",
            "offers.approve",
            "offers.send",
            "talent.view",
            "comms.view",
            "comms.send",
            "analytics.view",
            "career.view",
        ],
    },
    "recruiter": {
        "label": "Recruiter",
        "description": "Day-to-day recruiting across jobs and candidates",
        "permissions": [
            "org.view",
            "users.view",
            "jobs.view",
            "jobs.create",
            "jobs.edit",
            "jobs.publish",
            "candidates.view",
            "candidates.create",
            "candidates.edit",
            "candidates.export",
            "pipelines.view",
            "pipelines.move",
            "screening.view",
            "screening.manage",
            "screening.score",
            "interviews.view",
            "interviews.schedule",
            "interviews.feedback",
            "assessments.view",
            "assessments.create",
            "assessments.score",
            "offers.view",
            "offers.create",
            "offers.send",
            "talent.view",
            "talent.manage",
            "comms.view",
            "comms.send",
            "comms.templates",
            "analytics.view",
            "career.view",
            "career.edit",
            "portal.view",
        ],
    },
    "interviewer": {
        "label": "Interviewer",
        "description": "Conducts interviews and submits feedback",
        "permissions": [
            "jobs.view",
            "candidates.view",
            "pipelines.view",
            "interviews.view",
            "interviews.feedback",
            "assessments.view",
            "assessments.score",
            "comms.view",
        ],
    },
    "agency_recruiter": {
        "label": "Agency Recruiter",
        "description": "External recruiter with limited talent sourcing access",
        "permissions": [
            "jobs.view",
            "candidates.view",
            "candidates.create",
            "candidates.edit",
            "pipelines.view",
            "talent.view",
            "talent.sourcers",
            "comms.view",
            "comms.send",
        ],
    },
}

STAFF_PERSONAS["org_admin"]["permissions"] = all_permission_codes()


def permissions_for_persona(persona: str) -> list[str]:
    """Return default permission codes for a staff persona."""
    persona_def = STAFF_PERSONAS.get(persona)
    if not persona_def:
        return []
    return list(persona_def["permissions"] or [])


class IsOrgMember(BasePermission):
    """
    Authenticated user must belong to the request organization
    (set by OrgMiddleware) unless they are a platform admin.
    Safe for unauthenticated endpoints that opt out via AllowAny.
    """

    message = "You must be a member of this organization."

    def has_permission(self, request, view)
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "user_type", None) == "platform_admin" or user.is_superuser:
            return True
        if getattr(user, "user_type", None) == "candidate":
            # Candidate endpoints should use IsCandidateUser
            return getattr(view, "allow_candidates", False)
        org = getattr(request, "organization", None)
        if org is None:
            # Allow endpoints that do not require org context (e.g. /me, register)
            if getattr(view, "org_optional", False):
                return True
            return False
        return user.memberships.filter(
            organization=org,
            is_active=True,
        ).exists()


class HasPerm(BasePermission):
    """
    Check that the user's membership role includes required permission codes.

    Usage on a view:
        required_permissions = ["jobs.create"]
        permission_classes = [IsOrgMember, HasPerm]
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "user_type", None) == "platform_admin" or user.is_superuser:
            return True

        required = getattr(view, "required_permissions", None)
        if not required:
            # Optional method-specific map: {"GET": ["jobs.view"], "POST": ["jobs.create"]}
            method_map = getattr(view, "permission_map", {}) or {}
            required = method_map.get(request.method)
            if required is None and request.method in SAFE_METHODS:
                required = method_map.get("SAFE")
            if not required:
                return True

        if isinstance(required, str):
            required = [required]

        org = getattr(request, "organization", None)
        if org is None:
            return False

        membership = (
            user.memberships.filter(organization=org, is_active=True)
            .select_related("role")
            .first()
        )
        if membership is None:
            return False
        if membership.is_owner:
            return True

        role_perms = set(membership.role.permissions or []) if membership.role else set()
        return any(code in role_perms for code in required)


class IsCandidateUser(BasePermission):
    """Only candidate user type."""

    message = "Candidate access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "user_type", None) != "candidate"
        )


class IsStaffUser(BasePermission):
    """Staff (non-candidate) org members or platform admins."""

    message = "Staff access required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "user_type", None) == "platform_admin" or user.is_superuser:
            return True
        return getattr(user, "user_type", None) == "staff"
