"""
Django admin for jobs domain.
"""
from django.contrib import admin

from apps.jobs.models import Job, JobApproval, JobRecruiter, JobTemplate, ScreeningQuestion


class JobRecruiterInline(admin.TabularInline):
    model = JobRecruiter
    extra = 0
    raw_id_fields = ("user",)


class ScreeningQuestionInline(admin.TabularInline):
    model = ScreeningQuestion
    extra = 0
    fields = ("order", "prompt", "question_type", "is_required", "is_knockout")


class JobApprovalInline(admin.TabularInline):
    model = JobApproval
    extra = 0
    readonly_fields = ("decision", "decided_at", "decided_by")
    raw_id_fields = ("requested_by", "approver", "decided_by")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "organization",
        "status",
        "employment_type",
        "experience_level",
        "hiring_manager",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "employment_type", "experience_level", "remot_policy", "career_page_visible")
    search_fields = ("title", "slug", "decription")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("organization", "department", "office", "hiring_manager", "pipeline_template")
    inlines = [JobRecruiterInline, ScreeningQuestionInline, JobApprovalInline]
    readonly_fields = ("created_at", "updated_at", "published_at")


@admin.register(JobTemplate)
class JobTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "employment_type", "experience_level", "is_default")
    list_filter = ("employment_type", "is_default")
    search_fields = ("name", "title_template")
    raw_id_fields = ("organization",)


@admin.register(JobApproval)
class JobApprovalAdmin(admin.ModelAdmin):
    list_display = ("job", "decision", "requested_by", "approver", "decided_by", "decided_at")
    list_filter = ("decision",)
    raw_id_fields = ("organization", "job", "requested_by", "approver", "decided_by")


@admin.register(ScreeningQuestion)
class ScreeningQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "job", "question_type", "is_knockout", "order")
    list_filter = ("question_type", "is_knockout", "is_required")
    search_fields = ("prompt",)
    raw_id_fields = ("organization", "job")


@admin.register(JobRecruiter)
class JobRecruiterAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "is_primary")
    list_filter = ("is_primary",)
    raw_id_fields = ("organization", "job", "user")
