from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.accounts.models import (
    EmailVerificationToken,
    Invitation,
    Membership,
    PasswordResetToken,
    Role,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "user_type",
        "is_active",
        "email_verified_at",
        "is_staff",
    )
    list_filter = ("user_type", "is_active", "is_staff", "is_email_verified")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profile",
            {"fields": ("first_name", "last_name", "phone", "avatar", "timezone", "user_type")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "last_login_at", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "user_type", "is_staff"),
            },
        ),
    )
    readonly_fields = ("last_login", "last_login_at", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "organization", "is_system", "is_active")
    list_filter = ("is_system", "is_active")
    search_fields = ("name", "slug")
    raw_id_fields = ("organization",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "is_owner", "is_active", "joined_at")
    list_filter = ("is_owner", "is_active")
    search_fields = ("user__email", "organization__name")
    raw_id_fields = ("user", "organization", "role")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "role", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("email", "token")
    raw_id_fields = ("organization", "role", "invited_by", "accepted_by")
    readonly_fields = ("token",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "created_at")
    search_fields = ("user__email", "token")
    raw_id_fields = ("user",)
    readonly_fields = ("token",)


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "used_at", "created_at")
    search_fields = ("user__email", "token")
    raw_id_fields = ("user",)
    readonly_fields = ("token",)
