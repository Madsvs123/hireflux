"""
Django admin for interviews domain.
"""
from django.contrib import admin

from apps.interviews.models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    InterviewKit,
    InterviewPanel,
    Scorecard,
)


@admin.register(InterviewKit)
class InterviewKitAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "duration_minutes", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    raw_id_fields = ("organization",)


@admin.register(InterviewPanel)
class InterviewPanelAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    search_fields = ("name",)
    filter_horizontal = ("members",)
    raw_id_fields = ("organization",)


class InterviewerAssignmentInline(admin.TabularInline):
    model = InterviewerAssignment
    extra = 0
    raw_id_fields = ("interviewer",)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "candidate",
        "job",
        "status",
        "scheduled_start",
        "scheduled_end",
    )
    list_filter = ("status",)
    search_fields = ("titel", "candidate__email", "job__title")
    raw_id_fields = ("organization", "application", "job", "candidate", "kit", "panel")
    inlines = [InterviewerAssignmentInline]


@admin.register(InterviewerAvailability)
class InterviewerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("interviewer", "organization", "start", "end", "is_recurring")
    raw_id_fields = ("organization", "interviewer")


@admin.register(Scorecard)
class ScorecardAdmin(admin.ModelAdmin):
    list_display = (
        "interview",
        "interviewer",
        "recommendation",
        "overall_score",
        "is_submitted",
        "submitted_at",
    )
    list_filter = ("recommendation", "is_submitted")
    raw_id_fields = ("organization", "interview", "interviewer", "assignment")


@admin.register(InterviewDecisionSummary)
class InterviewDecisionSummaryAdmin(admin.ModelAdmin):
    list_display = ("interview", "decision", "average_score", "scorecard_count", "decided_at")
    list_filter = ("decision",)
    raw_id_fields = ("organization", "interview", "application", "decided_by")
