"""
Django admin for the billing domain.
"""
from django.contrib import admin

from apps.billing.models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    Plan,
    Subscription,
    UsageRecord,
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "price_per_month",
        "currency",
        "billing_cycle",
        "is_active",
        "is_default",
    )
    list_filter = ("billing_cycle", "is_active", "is_default")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "plan",
        "status",
        "seats",
        "cancel_at_period_end",
        "current_period_start",
        "current_period_end",
    )
    list_filter = ("status", "plan", "cancel_at_period_end")
    search_fields = ("organization__name", "plan__name")
    raw_id_fields = ("organization", "plan")
    readonly_fields = (
        "current_period_start",
        "current_period_end",
        "trial_end",
        "config",
        "created_at",
        "updated_at",
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "organization",
        "subscription",
        "status",
        "total",
        "currency",
        "issued_at",
        "due_at",
        "paid_at",
    )
    list_filter = ("status", "currency")
    search_fields = ("invoice_number", "organization__name")
    raw_id_fields = ("organization", "subscription")
    readonly_fields = ("line_items", "created_at", "updated_at")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "type",
        "brand",
        "last4",
        "is_default",
        "exp_month",
        "exp_year",
    )
    list_filter = ("type", "brand", "is_default")
    search_fields = ("organization__name", "brand", "last4")
    raw_id_fields = ("organization",)
    readonly_fields = ("provider_token_encrypted",)


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "invoice",
        "amount",
        "currency",
        "status",
        "provider",
        "provider_ref",
        "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = ("provider_ref", "invoice__invoice_number", "failure_reason")
    raw_id_fields = ("organization", "invoice")


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ("organization", "metric", "quantity", "recorded_at")
    list_filter = ("metric",)
    search_fields = ("organization__name",)
    raw_id_fields = ("organization",)
