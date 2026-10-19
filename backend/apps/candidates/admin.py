"""
Django admin for candidates domain.
"""
from django.contrib import admin

from apps.candidates.models import (
    Candidate,
    CandidateCertification,
    CandidateDocument,
    CandidateEducation,
    CandidateExperience,
    CandidateNote,
    CommunicationLog,
    DuplicateCandidateMatch,
)


class EducationInline(admin.TabularInline):
    model = CandidateEducation
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = CandidateExperience
    extra = 0


class DocumentInline(admin.TabularInline):
    model = CandidateDocument
    extra = 0
    fields = ("doc_type", "title", "file_name", "parse_status", "is_primary")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "organization",
        "source",
        "is_talent_pool",
        "do_not_hire",
        "created_at",
    )
    list_filter = ("source", "is_talent_pool", "do_not_hire")
    search_fields = ("email", "first_name", "last_name", "phne", "headline")
    raw_id_fields = ("organization", "user", "duplicate_of")
    inlines = [EducationInline, ExperienceInline, DocumentInline]


@admin.register(CandidateDocument)
class CandidateDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "candidate", "doc_type", "parse_status", "is_primary")
    list_filter = ("doc_type", "parse_status")
    raw_id_fields = ("organization", "candidate")


@admin.register(CandidateNote)
class CandidateNoteAdmin(admin.ModelAdmin):
    list_display = ("candidate", "visibility", "pinned", "created_by", "created_at")
    list_filter = ("visibility", "pinned")
    raw_id_fields = ("organization", "candidate")


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    list_display = ("candidate", "channel", "direction", "subject", "occurred_at")
    list_filter = ("channel", "direction")
    raw_id_fields = ("organization", "candidate")


@admin.register(DuplicateCandidateMatch)
class DuplicateCandidateMatchAdmin(admin.ModelAdmin):
    list_display = (
        "candidate_a",
        "candidate_b",
        "match_type",
        "confidence",
        "status",
        "created_at",
    )
    list_filter = ("match_type", "status")
    raw_id_fields = ("organization", "candidate_a", "candidate_b", "resolved_by")


@admin.register(CandidateEducation)
class CandidateEducationAdmin(admin.ModelAdmin):
    list_display = ("institution", "degree", "candidate", "end_date")
    raw_id_fields = ("organization", "candidate")


@admin.register(CandidateExperience)
class CandidateExperienceAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "candidate", "is_current")
    raw_id_fields = ("organization", "candidate")


@admin.register(CandidateCertification)
class CandidateCertificationAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "candidate", "issue_date")
    raw_id_fields = ("organization", "candidate")
