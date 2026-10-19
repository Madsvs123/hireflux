"""
Django admin for the integrations domain.
"""
from django.contrib import admin

from apps.integrations.models import (
    ApiKey,
    IntegrationConfig,
    IntegrationConnection,
    IntegrationProvider,
    WebhookDelivery,
    WebhookEndpoint,
)


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "category", "auth_type", "is_active")
    list_filter = ("category", "auth_type", "is_active")
    search_fields = ("key", "name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(IntegrationConnection)
class IntegrationConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "organization", "status", "last_synced_at")
    list_filter = ("status", "provider")
    search_fields = ("name", "provider__name")
    raw_id_fields = ("organization", "provider", "connected_by")
    readonly_fields = (
        "credentials_encrypted",
        "config",
        "last_synced_at",
        "last_error",
        "created_at",
        "updated_at",
    )


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ("connection", "key", "is_secret")
    list_filter = ("is_secret",)
    search_fields = ("key", "connection__name")
    raw_id_fields = ("organization", "connection")
    readonly_fields = ("value",)


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "url", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "url")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("secret", "events")


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event", "endpoint", "organization", "status", "attempts", "created_at")
    list_filter = ("status", "event")
    search_fields = ("event", "endpoint__name")
    raw_id_fields = ("organization", "endpoint")
    readonly_fields = (
        "payload",
        "request_headers",
        "response_status",
        "response_body",
        "attempts",
        "next_attempt_at",
    )


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "key_prefix", "is_active", "expires_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("name", "key_prefix")
    raw_id_fields = ("organization", "created_by", "updated_by")
    readonly_fields = ("key_hash", "key_prefix", "last_used_at")
