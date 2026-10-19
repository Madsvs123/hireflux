"""
Django admin for surveys domain.
"""
from django.contrib import admin

from apps.surveys.models import (
    SurveyInstance,
    SurveyInvitation,
    SurveyQuestion,
    SurveyResponse,
    SurveyTemplate,
)


@admin.register(SurveyTemplate)
class SurveyTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "survey_type", "is_active")
    list_filter = ("survey_type", "is_active")
    search_fields = ("name", "description")
    raw_id_fields = ("organization",)
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ("template", "question_text", "question_type", "is_required", "order")
    list_filter = ("question_type", "is_required")
    search_fields = ("question_text",)
    raw_id_fields = ("organization", "template")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")


@admin.register(SurveyInstance)
class SurveyInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "template",
        "organization",
        "candidate",
        "job",
        "status",
        "sent_at",
        "completed_at",
    )
    list_filter = ("status", "anonymous")
    search_fields = ("template__name", "candidate__email")
    raw_id_fields = ("organization", "template", "candidate", "job")
    readonly_fields = ("token", "created_by", "updated_by", "created_at", "updated_at")


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ("instance", "question", "answered_at")
    list_filter = ("answered_at",)
    raw_id_fields = ("organization", "instance", "question")
    readonly_fields = ("answer", "answered_at", "created_by", "updated_by", "created_at", "updated_at")


@admin.register(SurveyInvitation)
class SurveyInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "instance", "status", "sent_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("email",)
    raw_id_fields = ("organization", "instance")
    readonly_fields = ("created_by", "updated_by", "created_at", "updated_at")
