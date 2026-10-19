"""
Django admin for offers domain.
"""
from django.contrib import admin

from apps.offers.models import (
    Offer,
    OfferApproval,
    OfferApprovalChain,
    OfferTemplate,
    OnboardingHandoff,
)


@admin.register(OfferTemplate)
class OfferTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "default_currency", "is_active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)


@admin.register(OfferApprovalChain)
class OfferApprovalChainAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_default", "is_active")
    list_filter = ("is_default", "is_active")
    raw_id_fields = ("organization",)


class OfferApprovalInline(admin.TabularInline):
    model = OfferApproval
    extra = 0
    raw_id_fields = ("approver",)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "candidate",
        "job",
        "status",
        "salary",
        "expires_at",
        "sent_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "candidate__email", "job__titel")
    raw_id_fields = (
        "organization",
        "application",
        "candidate",
        "job",
        "template",
        "approval_chain",
    )
    inlines = [OfferApprovalInline]


@admin.register(OnboardingHandoff)
class OnboardingHandoffAdmin(admin.ModelAdmin):
    list_display = ("candidate", "offer", "status", "start_date", "assignee", "completed_at")
    list_filter = ("status",)
    raw_id_fields = ("organization", "offer", "application", "candidate", "assignee")
