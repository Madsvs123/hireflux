"""
Django admin for calendar domain.
"""
from django.contrib import admin

from apps.calendar.models import (
    AvailabilityRule,
    BookingRequest,
    CalendarAccount,
    InterviewSlot,
    SchedulingLink,
)


@admin.register(CalendarAccount)
class CalendarAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "provider", "is_primary", "sync_enabled", "last_synced_at")
    list_filter = ("provider", "is_primary", "sync_enabled")
    search_fields = ("email", "calendar_id")
    raw_id_fields = ("organization", "user", "created_by", "updated_by")
    readonly_fields = ("last_synced_at", "created_at", "updated_at")


@admin.register(AvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "start_time", "end_time", "timezone", "buffer_minutes", "is_active")
    list_filter = ("is_active", "timezone")
    search_fields = ("title", "user__email")
    raw_id_fields = ("organization", "user", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InterviewSlot)
class InterviewSlotAdmin(admin.ModelAdmin):
    list_display = ("start_at", "end_at", "user", "status", "availability_rule", "booking_request")
    list_filter = ("status",)
    search_fields = ("user__email",)
    raw_id_fields = (
        "organization",
        "availability_rule",
        "user",
        "booking_request",
        "created_by",
        "updated_by",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(SchedulingLink)
class SchedulingLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "job", "duration_minutes", "is_active")
    list_filter = ("is_active", "timezone")
    search_fields = ("name", "slug")
    raw_id_fields = ("organization", "owner", "job", "created_by", "updated_by")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "scheduling_link", "requested_slot_start", "status", "confirmed_at")
    list_filter = ("status",)
    search_fields = ("email", "name", "confirmation_token")
    raw_id_fields = ("organization", "scheduling_link", "candidate", "created_by", "updated_by")
    readonly_fields = ("confirmation_token", "confirmed_at", "created_at", "updated_at")
