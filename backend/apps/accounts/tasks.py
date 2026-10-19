"""
Celery email tasks (console/log style delivery).
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def dispatch_task(task, *args, **kwargs):
    """Enqueue a Celery task; fall back to sync call if the broker is unavailable."""
    try:
        return task.delay(*args, **kwargs)
    except Exception:
        logger.exception("Celery broker unavailable; running %s synchronously", task.name)
        return task(*args, **kwargs)


def _frontend_url(path: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}{path}"


@shared_task(name="accounts.send_verification_email")
def send_verification_email(user_id: str, token: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("send_verification_email: user %s not found", user_id)
        return False

    link = _frontend_url(f"/verify-email?token={token}")
    subject = "Verify your HireFlux email"
    message = (
        f"Hi {user.get_full_name() or user.email},\n\n"
        f"Please verify your email by visiting:\n{link}\n\n"
        f"If you did not create a HireFlux account, ignore this email.\n"
    )
    logger.info("EMAIL verification → %s | token=%s | link=%s", user.email, token, link)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL], fail_silently=True)
    return True


@shared_task(name="accounts.send_password_reset_email")
def send_password_reset_email(user_id: str, token: str):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("send_password_reset_email: user %s not found", user_id)
        return False

    link = _frontend_url(f"/reset-password?token={token}")
    subject = "Reset your HireFlux password"
    message = (
        f"Hi {user.get_full_name() or user.email},\n\n"
        f"Reset your password using this link:\n{link}\n\n"
        f"If you did not request a reset, ignore this email.\n"
    )
    logger.info("EMAIL password_reset → %s | token=%s | link=%s", user.email, token, link)
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    return True


@shared_task(name="accounts.send_invitation_email")
def send_invitation_email(invitation_id: str):
    from apps.accounts.models import Invitation

    try:
        invitation = Invitation.objects.select_related(
            "organization", "invited_by", "role"
        ).get(token=invitation_id)
    except Invitation.DoesNotExist:
        logger.warning("send_invitation_email: invitation %s not found", invitation_id)
        return False

    link = _frontend_url(f"/accept-invite?token={invitation.token}")
    inviter = ""
    if invitation.invited_by:
        inviter = invitation.invited_by.get_full_name() or invitation.invited_by.email
    role_name = invitation.role.name if invitation.role else "Member"
    subject = f"You're invited to {invitation.organization.name} on HireFlux"
    message = (
        f"You've been invited to join {invitation.organization.name}"
        f"{f' by {inviter}' if inviter else ''} as {role_name}.\n\n"
        f"{invitation.message}\n\n"
        f"Accept your invitation:\n{link}\n\n"
        f"This invitation expires at {invitation.expires_at.isoformat()}.\n"
    )
    logger.info(
        "EMAIL invitation → %s | org=%s | token=%s | link=%s",
        invitation.email,
        invitation.organization.slug,
        invitation.token,
        link,
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [invitation.email],
        fail_silently=True,
    )
    return True
