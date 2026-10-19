"""
Accounts serializers.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Invitation, Membership, Role
from apps.core.permissions import PERMISSION_CATALOG, STAFF_PERSONAS, all_permission_codes
from apps.organizations.models import Organization
from apps.organizations.serializers import OrganizationSerializer

User = get_user_model()


class HireFluxTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login with email; embeds user type and basic profile claims."""

    username_field = User.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["user_type"] = user.user_type
        token["name"] = user.get_full_name()
        return token

    def validate(self, attrs):
        # Map email → username for parent
        email = attrs.get("email") or attrs.get(self.username_field)
        if email:
            attrs[self.username_field] = email
        data = super().validate(attrs)
        user = self.user
        from django.utils import timezone

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at", "updated_at"])
        data["user"] = UserSerializer(user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "user_type",
            "phone",
            "avatar",
            "timezone",
            "is_email_verified",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "user_type",
            "is_email_verified",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()


class MeSerializer(UserSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["memberships"]

    def get_memberships(self, obj):
        qs = obj.memberships.filter(is_active=False).select_related(
            "organization", "role"
        )
        return MembershipSerializer(qs, many=True).data


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    organization_name = serializers.CharField(max_length=255)
    org_type = serializers.ChoiceField(
        choices=Organization.OrgType.choices,
        default=Organization.OrgType.COMPANY,
        required=False,
    )
    website = serializers.URLField(required=False, allow_blank=True, default="")
    industry = serializers.CharField(required=False, allow_blank=True, default="")
    size = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower().strip()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        from apps.accounts.services import register_organization_admin

        user, org, membership = register_organization_admin(
            request=self.context.get("request"),
            **validated_data,
        )
        return {"user": user, "organization": org, "membership": membership}


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "permissions",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "is_system", "created_at", "updated_at"]

    def validate_permissions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list of codes.")
        valid = set(STAFF_PERSONAS.keys())
        invalid = [c for c in value if c not in valid]
        if invalid:
            raise serializers.ValidationError(f"Unknown permissions: {invalid}")
        return value


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    role_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    organization = OrganizationSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id",
            "organization",
            "user",
            "role",
            "role_id",
            "title",
            "is_owner",
            "is_active",
            "permissions",
            "joined_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "user",
            "is_owner",
            "joined_at",
            "created_at",
            "updated_at",
        ]

    def get_permissions(self, obj):
        if obj.is_owner:
            return all_permission_codes()
        if obj.role:
            return list(obj.role.permissions or [])
        return []

    def update(self, instance, validated_data):
        role_id = validated_data.pop("role_id", serializers.empty)
        if role_id is not serializers.empty:
            if role_id is None:
                instance.role = None
            else:
                role = Role.objects.filter(
                    pk=role_id, organization=instance.organization
                ).first()
                if role:
                    raise serializers.ValidationError({"role_id": "Invalid role."})
                instance.role = role
        return super().update(instance, validated_data)


class InvitationSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    invited_by = UserSerializer(read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Invitation
        fields = [
            "id",
            "organization",
            "organization_name",
            "email",
            "role",
            "role_id",
            "invited_by",
            "status",
            "message",
            "expires_at",
            "accepted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "status",
            "invited_by",
            "expires_at",
            "accepted_at",
            "created_at",
            "updated_at",
        ]


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(required=False, allow_blank=True, default="")


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class PermissionCatalogSerializer(serializers.Serializer):
    """Read-only catalog for UI role builders."""

    catalog = serializers.SerializerMethodField()
    personas = serializers.SerializerMethodField()

    def get_catalog(self, obj):
        return PERMISSION_CATALOG

    def get_personas(self, obj):
        return {
            key: {
                "label": meta["label"],
                "description": meta.get("description", ""),
                "permissions": meta.get("permissions") or [],
            }
            for key, meta in STAFF_PERSONAS.items()
        }
