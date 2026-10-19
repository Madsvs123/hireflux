"""
Serializers for the billing domain.

Payment provider tokens are write-only; invoice and transaction history is
read-only; subscription status transitions happen through explicit actions.
"""
from rest_framework import serializers

from apps.billing.models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    Plan,
    Subscription,
    UsageRecord,
)


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price_per_month",
            "currency",
            "billing_cycle",
            "features",
            "limits",
            "is_active",
            "is_default",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_price = serializers.DecimalField(
        source="plan.price_per_month", max_digits=10, decimal_places=2, read_only=True
    )
    plan_currency = serializers.CharField(source="plan.currency", read_only=True)
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "plan_name",
            "plan_price",
            "plan_currency",
            "organization",
            "organization_name",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "trial_end",
            "seats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
            "trial_end",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class ChangePlanSerializer(serializers.Serializer):
    """Input for change-plan / preview-change actions."""

    plan = serializers.UUIDField()
    immediate = serializers.BooleanField(required=False, default=True)


class CancelSubscriptionSerializer(serializers.Serializer):
    """Input for the cancel action."""

    immediate = serializers.BooleanField(required=False, default=False)


class InvoiceSerializer(serializers.ModelSerializer):
    subscription_plan = serializers.CharField(
        source="subscription.plan.name", read_only=True, default=None
    )
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "subscription",
            "subscription_plan",
            "organization",
            "organization_name",
            "invoice_number",
            "status",
            "subtotal",
            "tax",
            "total",
            "currency",
            "issued_at",
            "due_at",
            "paid_at",
            "line_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentMethodSerializer(serializers.ModelSerializer):
    provider_token = serializers.JSONField(
        write_only=True,
        required=False,
        default=dict,
        help_text="Provider token; encrypted before storage.",
    )

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "type",
            "brand",
            "last4",
            "exp_month",
            "exp_year",
            "is_default",
            "provider_token",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        from apps.billing.crypto import encrypt_value

        provider_token = validated_data.pop("provider_token", {}) or {}
        validated_data["provider_token_encrypted"] = (
            {"token": encrypt_value(provider_token)} if provider_token else {}
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from apps.billing.crypto import encrypt_value

        provider_token = validated_data.pop("provider_token", None)
        if provider_token is not None:
            instance.provider_token_encrypted = (
                {"token": encrypt_value(provider_token)} if provider_token else {}
            )
            instance.save(update_fields=["provider_token_encrypted", "updated_at"])
        return super().update(instance, validated_data)


class PaymentTransactionSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True, default=None
    )

    class Meta:
        model = PaymentTransaction
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "amount",
            "currency",
            "status",
            "provider",
            "provider_ref",
            "failure_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = [
            "id",
            "metric",
            "quantity",
            "recorded_at",
            "created_at",
        ]
        read_only_fields = fields
