"""
Django admin for assessments domain.
"""
from django.contrib import admin

from apps.assessments.models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 0


@admin.register(AssessmentTemplate)
class AssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "assessment_type", "passing_score", "is_active")
    list_filter = ("assessment_type", "is_active")
    search_fields = ("name",)
    raw_id_fields = ("organization",)
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentAssignment)
class AssessmentAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "template",
        "candidate",
        "status",
        "score_percent",
        "passed",
        "knockout_failed",
        "due_at",
    )
    list_filter = ("status", "passed", "knockout_failed")
    raw_id_fields = ("organization", "template", "application", "candidate", "job")


@admin.register(AssessmentAnswer)
class AssessmentAnswerAdmin(admin.ModelAdmin):
    list_display = ("assignment", "question", "is_correct", "points_awarded")
    raw_id_fields = ("organization", "assignment", "question")


@admin.register(CandidateRating)
class CandidateRatingAdmin(admin.ModelAdmin):
    list_display = ("candidate", "rater", "score", "application", "created_at")
    raw_id_fields = ("organization", "candidate", "application", "rater")


@admin.register(HiringComment)
class HiringCommentAdmin(admin.ModelAdmin):
    list_display = ("candidate", "author", "parent", "is_resolved", "created_at")
    search_fields = ("boday",)
    raw_id_fields = ("organization", "candidate", "application", "author", "parent")
    filter_horizontal = ("mentions",)
