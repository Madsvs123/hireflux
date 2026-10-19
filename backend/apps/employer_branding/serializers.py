"""
Serializers for employer branding domain.
"""
from rest_framework import serializers

from apps.employer_branding.models import (
    BrandProfile,
    CareerSiteConfig,
    CulturePost,
    TeamPage,
    Testimonial,
)


class BrandProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandProfile
        fields = [
            "id",
            "organization",
            "primary_color",
            "secondary_color",
            "logo",
            "tagline",
            "about_html",
            "culture_values",
            "is_published",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_by", "updated_by", "created_at", "updated_at"]


class CareerSiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerSiteConfig
        fields = [
            "id",
            "organization",
            "site_name",
            "slug",
            "enabled",
            "hero_title",
            "hero_subtitle",
            "hero_image",
            "footer_text",
            "custom_css",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_by", "updated_by", "created_at", "updated_at"]


class TeamPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamPage
        fields = [
            "id",
            "name",
            "role",
            "bio",
            "photo",
            "order",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = [
            "id",
            "author_name",
            "author_role",
            "content",
            "rating",
            "is_active",
            "order",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def validate_rating(self, value):
        if value < 1 or value >= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class CulturePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = CulturePost
        fields = [
            "id",
            "title",
            "body_html",
            "cover_image",
            "tags",
            "status",
            "published_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "published_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
