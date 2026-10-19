"""
Django admin for employer branding domain.
"""
from django.contrib import admin

from apps.employer_branding.models import (
    BrandProfile,
    CareerSiteConfig,
    CulturePost,
    TeamPage,
    Testimonial,
)


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "is_published",
        "primary_color",
        "tagline",
        "updated_at",
    )
    list_filter = ("is_published",)
    search_fields = ("tagline", "about_html")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CareerSiteConfig)
class CareerSiteConfigAdmin(admin.ModelAdmin):
    list_display = ("organization", "site_name", "slug", "enabled", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("site_name", "slug", "hero_title")
    prepopulated_fields = {"slug": ("site_name",)}
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeamPage)
class TeamPageAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "order", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "role", "bio")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author_name", "author_role", "rating", "is_active", "order")
    list_filter = ("is_active", "rating")
    search_fields = ("author_name", "author_role", "content")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CulturePost)
class CulturePostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "published_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "body_html", "tags")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("published_at", "created_at", "updated_at")
