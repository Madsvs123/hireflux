"""
Django admin for sources domain.
"""
from django.contrib import admin

from apps.sources.models import (
    CampaignRecipient,
    CandidateSourceAttribution,
    SourceChannel,
    SourcingCampaign,
)


@admin.register(SourceChannel)
class SourceChannelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "channel_type",
        "cost_per_post",
        "is_active",
    )
    list_filter = ("channel_type", "is_active")
    search_fields = ("name", "url", "notes")
    raw_id_fields = ("organization",)
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(SourcingCampaign)
class SourcingCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "channel",
        "job",
        "status",
        "started_at",
        "ended_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "goal")
    raw_id_fields = ("organization", "channel", "job", "talent_pool")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "campaign", "organization", "candidate", "status", "sent_at")
    list_filter = ("status",)
    search_fields = ("email",)
    raw_id_fields = ("organization", "campaign", "candidate")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(CandidateSourceAttribution)
class CandidateSourceAttributionAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "channel",
        "campaign",
        "attribution_date",
        "utm_source",
    )
    list_filter = ("attribution_date", "utm_source", "utm_medium")
    search_fields = ("source_detail", "utm_source", "utm_campaign", "candidate__email")
    raw_id_fields = ("organization", "candidate", "channel", "campaign")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
