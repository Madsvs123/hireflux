"""
Django admin for events domain.
"""
from django.contrib import admin

from apps.events.models import EventRegistration, EventSession, EventTask, RecruitingEvent


@admin.register(RecruitingEvent)
class RecruitingEventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "event_type",
        "status",
        "start_at",
        "end_at",
        "is_virtual",
        "capacity",
    )
    list_filter = ("event_type", "status", "is_virtual")
    search_fields = ("name", "description", "location")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EventSession)
class EventSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "speaker", "start_at", "end_at", "room")
    list_filter = ("room",)
    search_fields = ("title", "speaker", "description", "room")
    raw_id_fields = ("organization", "event", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "event", "candidate", "status", "registered_at", "checked_in_at")
    list_filter = ("status",)
    search_fields = ("email", "first_name", "last_name")
    raw_id_fields = ("organization", "event", "candidate", "created_by", "updated_by")
    readonly_fields = ("registered_at", "checked_in_at", "created_at", "updated_at")


@admin.register(EventTask)
class EventTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "assignee", "status", "due_at")
    list_filter = ("status",)
    search_fields = ("title", "notes")
    raw_id_fields = ("organization", "event", "assignee", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")
