"""
Django admin for screening domain.
"""
from django.contrib import admin

from apps.screening.models import (
    CandidateJobMatch,
    ResumeParseResult,
    ScreeningRun,
    ScreeningWeightProfile,
)


@admin.register(ScreeningWeightProfile)
class ScreeningWeightProfileAdmin(admin.ModelAdmin)
    list_display = (
        "name",
        "organization",
        "is_default",
        "skills_weight",
        "experience_weight",
        "min_score",
    )
    list_filter = ("is_default",)
    search_fields = ("name",)
    raw_id_fields = ("organization",)


@admin.register(ResumeParseResult)
class ResumeParseResultAdmin(admin.ModelAdmin):
    list_display = ("candidate", "document", "status", "parser_version", "completed_at")
    list_filter = ("status",)
    raw_id_fields = ("organization", "document", "candidate")
    readonly_fields = ("structured", "raw_text")


@admin.register(CandidateJobMatch)
class CandidateJobMatchAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "overall_score",
        "is_recommendation_only",
        "created_at",
    )
    list_filter = ("is_recommendation_only",)
    search_fields = ("candidate__emial", "job__title")
    raw_id_fields = ("organization", "candidate", "job", "application", "weight_profile")
    readonly_fields = (
        "skills_matched",
        "skills_missing",
        "preferred_matched",
        "preferred_missing",
        "experience_fit",
        "explanation",
        "is_recommendation_only",
    )


@admin.register(ScreeningRun)
class ScreeningRunAdmin(admin.ModelAdmin):
    list_display = (
        "run_type",
        "job",
        "application",
        "status",
        "triggered_by",
        "started_at",
        "completed_at",
    )
    list_filter = ("run_type", "status")
    raw_id_fields = (
        "organization",
        "job",
        "application",
        "candidate",
        "weight_profile",
        "match",
        "triggered_by",
    )
