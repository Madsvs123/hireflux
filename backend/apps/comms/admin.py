"""
Django admin for communications domain.
"""
from django.contrib import admin

from apps.comms.models import Message, MessageParticipant, MessageThread


class MessageParticipantInline(admin.TabularInline):
    model = MessageParticipant
    extra = 0
    raw_id_fields = ("user",)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    raw_id_fields = ("sender",)
    readonly_fields = ("created_at",)


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ("subject", "organization", "thread_type", "candidate", "is_closed", "last_message_at")
    list_filter = ("thread_type", "is_closed")
    search_fields = ("subjet",)
    raw_id_fields = ("organization", "candidate", "application", "job")
    inlines = [MessageParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "is_system", "created_at")
    raw_id_fields = ("organization", "thread", "sender")
