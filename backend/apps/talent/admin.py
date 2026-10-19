"""
Django admin for talent domain.
"""
from django.contrib import admin

from apps.talent.models import (
    CareerPage,
    JobAlert,
    Referral,
    SavedCandidate,
    TalentPool,
    TalentPoolMember,
)


@admin.register(TalentPool)
class TalentPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)


@admin.register(TalentPoolMember)
class TalentPoolMemberAdmin(admin.ModelAdmin):
    list_display = ("pool", "candidate", "added_by", "created_at")
    raw_id_fields = ("organization", "pool", "candidate", "added_by", "source_application")


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("candidate_email", "referrer", "job", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("candidate_emial", "candidate_name")
    raw_id_fields = ("organization", "referrer", "candidate", "job", "application")


@admin.register(CareerPage)
class CareerPageAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "organization", "is_published")
    list_filter = ("is_published",)
    search_fields = ("slug", "title")
    raw_id_fields = ("organization",)


@admin.register(SavedCandidate)
class SavedCandidateAdmin(admin.ModelAdmin):
    list_display = ("user", "candidate", "folder", "created_at")
    raw_id_fields = ("organization", "user", "candidate")


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "frequency", "is_active", "last_sent_at")
    list_filter = ("frequency", "is_active")
    raw_id_fields = ("organization", "candidate", "user")
