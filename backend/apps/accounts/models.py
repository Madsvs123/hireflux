"""
Accounts models: User, Role, Membership, Invitation, tokens.
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.permissions import STAFF_PERSONAS, all_permission_codes


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("user_type", User.UserType.STAFF)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", User.UserType.PLATFORM_ADMIN)
        extra_fields.setdefault("is_email_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class UserType(models.TextChoices):
        STAFF = "staff", "Staff"
        CANDIDATE = "candidate", "Candidate"
        PLATFORM_ADMIN = "platform_admin", "Platform Admin"

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    user_type = models.CharField(
        max_length=32,
        choices=UserType.choices,
        default=UserType.STAFF,
        db_index=True,
    )
    phone = models.CharField(max_length=32, blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    timezone = models.CharField(max_length=64, blank=True, default="UTC")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]
        indexes = [
            models.Index(fields=["user_type", "is_active"]),
        ]

    def __str__(self):
        return self.email

    def get_full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]


class Role(TimeStampedModel):
    """Organization-scoped role with a list of permission codes."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128)
    description = models.TextField(blank=True, default="")
    permissions = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System roles seeded from STAFF_PERSONAS; not deletable.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.organization})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "role"
        super().save(*args, **kwargs)

    @classmethod
    def seed_defaults(cls, organization):
        """Create default roles from STAFF_PERSONAS for an organization."""
        created = []
        for slug, meta in STAFF_PERSONAS.items():
            role, was_created = cls.objects.update_or_create(
                organization=organization,
                slug=slug,
                defaults={
                    "name": meta["label"],
                    "description": meta.get("description", ""),
                    "permissions": list(meta.get("permissions") or all_permission_codes()),
                    "is_system": True,
                    "is_active": True,
                },
            )
            if was_created:
                created.append(role)
        return created


class Membership(TimeStampedModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )
    title = models.CharField(max_length=128, blank=True, default="")
    is_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("organization", "user")]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} ∈ {self.organization}"

    def has_perm_code(self, code: str) -> bool:
        if self.is_owner:
            return True
        if not self.role:
            return False
        return code in (self.role.permissions or [])


class Invitation(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(db_index=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    message = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["email", "status"]),
        ]

    def __str__(self):
        return f"Invite {self.email} → {self.organization}"

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create_invitation(cls, *, organization, email, role=None, invited_by=None, message=""):
        days = getattr(settings, "INVITATION_EXPIRY_DAYS", 7)
        return cls.objects.create(
            organization=organization,
            email=email.lower().strip(),
            role=role,
            invited_by=invited_by,
            message=message or "",
            token=cls.generate_token(),
            expires_at=timezone.now() + timedelta(days=days),
        )

    def is_valid(self) -> bool:
        if self.status == self.Status.PENDING:
            return False
        if self.expires_at >= timezone.now():
            return False
        return True

    def mark_expired_if_needed(self):
        if self.status == self.Status.PENDING and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status", "updated_at"])


class PasswordResetToken(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create_for_user(cls, user):
        hours = getattr(settings, "PASSWORD_RESET_TOKEN_HOURS", 24)
        return cls.objects.create(
            user=user,
            token=cls.generate_token(),
            expires_at=timezone.now() + timedelta(hours=hours),
        )

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at < timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])


class EmailVerificationToken(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create_for_user(cls, user):
        hours = getattr(settings, "EMAIL_VERIFICATION_TOKEN_HOURS", 48)
        return cls.objects.create(
            user=user,
            token=cls.generate_token(),
            expires_at=timezone.now() + timedelta(hours=hours),
        )

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at", "updated_at"])
