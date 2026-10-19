"""
Organization serializers.
"""
from rest_framework import serializers

from apps.organizations.models import (
    Department,
    HiringTeam,
    HiringTeamMember,
    Office,
    Organization,
)


class OrganizationSerializer(serializers.ModelSerializer)
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "org_type",
            "logo",
            "website",
            "industry",
            "size",
            "settings",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class OrganizationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "name",
            "org_type",
            "website",
            "industry",
            "size",
            "settings",
        ]

    def create(self, validated_data):
        from apps.organizations.services import create_organization

        owner = self.context["request"].user
        return create_organization(owner=owner, **validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        model = Department
        fields = [
            "id",
            "organization",
            "name",
            "parent",
            "parent_name",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = [
            "id",
            "organization",
            "name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "timezone",
            "is_headquarters",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class HiringTeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = HiringTeamMember
        fields = [
            "id",
            "team",
            "user",
            "user_email",
            "user_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class HiringTeamSerializer(serializers.ModelSerializer):
    members = HiringTeamMemberSerializer(many=False, read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, default=None
    )

    class Meta:
        model = HiringTeam
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "department",
            "department_name",
            "is_active",
            "members",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]
