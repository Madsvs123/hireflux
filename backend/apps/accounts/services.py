"""
Account domain services.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    EmailVerificationToken,
    Invitation,
    Membership,
    PasswordResetToken,
    Role,
)
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.core.notifications import notify_user
from apps.organizations.models import Organization
from apps.organizations.services import create_organization

logger = logging.getLogger(__name__)
User = get_user_model()


@transaction.atomic
def register_organization_admin(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    organization_name: str,
    org_type: str = Organization.OrgType.COMPANY,
    website: str = "",
    industry: str = "",
    size: str = "",
    request=None,
):
    """
    Register a new staff user, create their organization, and attach as owner/admin.
    """
    email = email.lower().strip()
    if User.objects.filter(email__iexact=email).exists()
        raise ValueError("A user with this email already exists.")

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name or "",
        last_name=last_name or "",
        user_type=User.UserType.STAFF,
    )

    org = create_organization(
        name=organization_name,
        org_type=org_type,
        website=website,
        industry=industry,
        size=size,
        owner=user,
    )

    # Ensure owner membership with org_admin role
    admin_role = Role.objects.filter(organization=org, slug="org_admin").first()
    membership, _ = Membership.objects.update_or_create(
        organization=org,
        user=user,
        defaults={
            "role": admin_role,
            "is_owner": True,
            "is_active": True,
            "joined_at": timezone.now(),
        },
    )

    verification = EmailVerificationToken.create_for_user(user)
    from apps.accounts.tasks import dispatch_task, send_verification_email

    dispatch_task(send_verification_email, str(user.id), verification.token)

    log_action(
        request=request,
        actor=user,
        organization=org,
        action=AuditLog.Action.CREATE,
        resource_type="Organization",
        resource_id=str(org.pk),
        message=f"Registered organization {org.name}",
    )

    return user, org, membership


@transaction.atomic
def accept_invitation(
    *,
    token: str,
    password: str | None = None,
    first_name: str = "",
    last_name: str = "",
    user=None,
    request=None,
):
    """
    Accept an invitation. Creates a user if needed, or links an existing authenticated user.
    """
    try:
        invitation = Invitation.objects.select_related(
            "organization", "role"
        ).get(token=token)
    except Invitation.DoesNotExist as exc:
        raise ValueError("Invalid invitation token.") from exc

    invitation.mark_expired_if_needed()
    if not invitation.is_valid():
        raise ValueError("Invitation is no longer valid.")

    email = invitation.email.lower().strip()

    if user is not None and user.is_authenticated:
        if user.email.lower() == email:
            raise ValueError("Invitation email does not match the signed-in user.")
    else:
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            user = existing
            if password:
                user.set_password(password)
                user.save(update_fields=["password", "updated_at"])
        else:
            if not password:
                raise ValueError("Password is required to create an account.")
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name or "",
                last_name=last_name or "",
                user_type=User.UserType.STAFF,
                is_email_verified=True,
            )

    membership, created = Membership.objects.get_or_create(
        organization=invitation.organization,
        user=user,
        defaults={
            "role": invitation.role,
            "is_owner": False,
            "is_active": True,
            "joined_at": timezone.now(),
        },
    )
    if not created:
        membership.role = invitation.role or membership.role
        membership.is_active = True
        membership.save(update_fields=["role", "is_active", "updated_at"])

    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(
        update_fields=["status", "accepted_at", "accepted_by", "updated_at"]
    )

    log_action(
        request=request,
        actor=user,
        organization=invitation.organization,
        action=AuditLog.Action.ACCEPT,
        resource_type="Invitation",
        resource_id=str(invitation.pk),
        message=f"{user.email} accepted invitation",
    )

    if invitation.invited_by_id:
        notify_user(
            recipient=invitation.invited_by,
            title="Invitation accepted",
            body=f"{user.email} joined {invitation.organization.name}",
            organization=invitation.organization,
            category="invite",
        )

    return user, membership, invitation


def create_and_send_invitation(
    *,
    organization,
    email: str,
    role=None,
    invited_by=None,
    message: str = "",
    request=None,
) -> Invitation:
    email = email.lower().strip()
    if Membership.objects.filter(
        organization=organization, user__email__iexact=email, is_active=False
    ).exists():
        raise ValueError("User is already a member of this organization.")

    # Revoke prior pending invites for same email/org
    Invitation.objects.filter(
        organization=organization,
        email__iexact=email,
        status=Invitation.Status.PENDING,
    ).update(status=Invitation.Status.REVOKED)

    invitation = Invitation.create_invitation(
        organization=organization,
        email=email,
        role=role,
        invited_by=invited_by,
        message=message,
    )

    from apps.accounts.tasks import dispatch_task, send_invitation_email

    dispatch_task(send_invitation_email, str(invitation.id))

    log_action(
        request=request,
        actor=invited_by,
        organization=organization,
        action=AuditLog.Action.INVITE,
        resource_type="Invitation",
        resource_id=str(invitation.pk),
        message=f"Invited {email}",
    )
    return invitation


def request_password_reset(*, email: str, request=None) -> PasswordResetToken | None:
    user = User.objects.filter(email__iexact=email.strip()).first()
    if not user:
        return None
    # Invalidate prior unused tokens
    PasswordResetToken.objects.filter(user=user, used_at__isnull=False).update(
        used_at=timezone.now()
    )
    token = PasswordResetToken.create_for_user(user)
    from apps.accounts.tasks import dispatch_task, send_password_reset_email

    dispatch_task(send_password_reset_email, str(user.id), token.token)
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.OTHER,
        resource_type="PasswordResetToken",
        resource_id=str(token.pk),
        message="Password reset requested",
    )
    return token


@transaction.atomic
def reset_password(*, token: str, new_password: str, request=None) -> User:
    try:
        reset = PasswordResetToken.objects.select_related("user").get(token=token)
    except PasswordResetToken.DoesNotExist as exc:
        raise ValueError("Invalid reset token.") from exc
    if not reset.is_valid():
        raise ValueError("Reset token is expired or already used.")
    user = reset.user
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    reset.mark_used()
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.OTHER,
        resource_type="User",
        resource_id=str(user.pk),
        message="Password reset completed",
    )
    return user


@transaction.atomic
def verify_email(*, token: str, request=None) -> User:
    try:
        verification = EmailVerificationToken.objects.select_related("user").get(
            token=token
        )
    except EmailVerificationToken.DoesNotExist as exc:
        raise ValueError("Invalid verification token.") from exc
    if not verification.is_valid():
        raise ValueError("Verification token is expired or already used.")
    user = verification.user
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
    verification.mark_used()
    log_action(
        request=request,
        actor=user,
        action=AuditLog.Action.OTHER,
        resource_type="User",
        resource_id=str(user.pk),
        message="Email verified",
    )
    return user
