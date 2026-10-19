"""
Billing ViewSets: plans, subscriptions, invoices, payment methods,
transactions, usage, and the combined billing overview.
"""
import csv
import io
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services
from apps.billing.models import (
    Invoice,
    PaymentMethod,
    PaymentTransaction,
    Plan,
    Subscription,
    UsageRecord,
)
from apps.billing.serializers import (
    CancelSubscriptionSerializer,
    ChangePlanSerializer,
    InvoiceSerializer,
    PaymentMethodSerializer,
    PaymentTransactionSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    UsageRecordSerializer,
)
from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Platform plan catalog (org-visible, not org-scoped)."""

    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["billing.view"]}
    filterset_fields = ["billing_cycle", "is_default"]
    search_fields = ["name", "slug", "description"]
    ordering = ["price_per_month"]


class SubscriptionViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = Subscription.objects.select_related("plan", "organization")
    serializer_class = SubscriptionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["billing.view"],
        "POST": ["billing.manage"],
        "PUT": ["billing.manage"],
        "PATCH": ["billing.manage"],
        "DELETE": ["billing.manage"],
    }
    filterset_fields = ["plan", "status"]
    search_fields = ["plan__name", "organization__name"]
    ordering = ["-created_at"]
    audit_resource_type = "Subscription"

    def get_permissions(self):
        action_perms = {
            "change_plan": ["billing.manage"],
            "cancel": ["billing.manage"],
            "resume": ["billing.manage"],
            "preview_change": ["billing.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Subscribe the org to a plan (replaces any active subscription)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data.get("plan")
        if not plan or not plan.is_active:
            return Response(
                {"detail": "Plan not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        subscription = services.subscribe_org(
            request.organization,
            plan,
            actor=request.user,
            seats=serializer.validated_data.get("seats", 1),
        )
        return Response(
            self.get_serializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        subscription = self.get_object()
        ser = ChangePlanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan = Plan.objects.filter(pk=ser.validated_data["plan"], is_active=True).first()
        if not plan:
            return Response(
                {"detail": "Plan not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        subscription = services.change_subscription_plan(
            subscription,
            plan,
            actor=request.user,
            immediate=ser.validated_data.get("immediate", True),
        )
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        ser = CancelSubscriptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subscription = services.cancel_subscription(
            subscription,
            actor=request.user,
            immediate=ser.validated_data.get("immediate", False),
        )
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        subscription = self.get_object()
        subscription = services.resume_subscription(subscription, actor=request.user)
        return Response(self.get_serializer(subscription).data)

    @action(detail=True, methods=["post"], url_path="preview-change")
    def preview_change(self, request, pk=None):
        """Preview proration for a plan change without applying it."""
        subscription = self.get_object()
        ser = ChangePlanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan = Plan.objects.filter(pk=ser.validated_data["plan"], is_active=True).first()
        if not plan:
            return Response(
                {"detail": "Plan not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(services.preview_plan_change(subscription, plan))


class PayInvoiceSerializer(serializers.Serializer):
    """Input for the invoice pay (mock) action."""

    provider = serializers.CharField(required=False, default="mock")
    provider_ref = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(
        required=False, max_digits=12, decimal_places=2, allow_null=True
    )


class InvoiceViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Invoice.objects.select_related("subscription", "subscription__plan", "organization")
    serializer_class = InvoiceSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["billing.view"]}
    filterset_fields = ["subscription", "status"]
    search_fields = ["invoice_number", "organization__name"]
    ordering = ["-issued_at", "-created_at"]

    def get_permissions(self):
        action_perms = {
            "pay": ["billing.manage"],
            "download": ["billing.view"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Record a (mock) payment and settle the invoice."""
        invoice = self.get_object()
        ser = PayInvoiceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        transaction_obj = services.record_payment(
            invoice,
            actor=request.user,
            provider=ser.validated_data.get("provider", "mock"),
            provider_ref=ser.validated_data.get("provider_ref", ""),
            amount=ser.validated_data.get("amount"),
        )
        return Response(
            {
                "invoice": InvoiceSerializer(invoice).data,
                "transaction": PaymentTransactionSerializer(transaction_obj).data,
            }
        )

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Download the invoice as CSV."""
        invoice = self.get_object()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["description", "quantity", "unit_price", "amount"])
        for item in invoice.line_items or []:
            writer.writerow(
                [
                    item.get("description", ""),
                    item.get("quantity", ""),
                    item.get("unit_price", ""),
                    item.get("amount", ""),
                ]
            )
        writer.writerow([])
        writer.writerow(["subtotal", invoice.subtotal])
        writer.writerow(["tax", invoice.tax])
        writer.writerow(["total", invoice.total])
        writer.writerow(["currency", invoice.currency])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{invoice.invoice_number}.csv"'
        )
        return response


class PaymentMethodViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["billing.view"],
        "POST": ["billing.manage"],
        "PUT": ["billing.manage"],
        "PATCH": ["billing.manage"],
        "DELETE": ["billing.manage"],
    }
    filterset_fields = ["type", "is_default", "brand"]
    search_fields = ["brand", "last4"]
    ordering = ["-is_default", "-created_at"]
    audit_resource_type = "PaymentMethod"

    def get_permissions(self):
        action_perms = {
            "set_default": ["billing.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def perform_create(self, serializer):
        super().perform_create(serializer)
        instance = serializer.instance
        if instance.is_default:
            PaymentMethod.objects.for_org(self.request.organization).exclude(
                pk=instance.pk
            ).update(is_default=False)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        if instance.is_default:
            PaymentMethod.objects.for_org(self.request.organization).exclude(
                pk=instance.pk
            ).update(is_default=False)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        method = self.get_object()
        method = services.set_default_payment_method(method, actor=request.user)
        return Response(self.get_serializer(method).data)


class PaymentTransactionViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.select_related("invoice")
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["billing.view"]}
    filterset_fields = ["invoice", "status", "provider"]
    search_fields = ["provider_ref", "failure_reason"]
    ordering = ["-created_at"]


class UsageViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = UsageRecord.objects.all()
    serializer_class = UsageRecordSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["billing.view"]}
    filterset_fields = ["metric"]
    ordering = ["-recorded_at"]

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Latest recorded value for each metric."""
        data = {}
        for metric in UsageRecord.Metric.values:
            latest = (
                UsageRecord.objects.for_org(request.organization)
                .filter(metric=metric)
                .order_by("-recorded_at")
                .first()
            )
            data[metric] = {
                "quantity": latest.quantity if latest else 0,
                "recorded_at": latest.recorded_at if latest else None,
            }
        return Response(data)

    @action(detail=False, methods=["get"], url_path="usage-by-period")
    def usage_by_period(self, request):
        """Aggregated usage over a date range, bucketed by hour/day/month."""
        metric = request.query_params.get("metric")
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        granularity = request.query_params.get("granularity", "day")

        qs = UsageRecord.objects.for_org(request.organization)
        if metric:
            qs = qs.filter(metric=metric)
        if start:
            qs = qs.filter(recorded_at__gte=start)
        if end:
            qs = qs.filter(recorded_at__gte=end)
        if not start and not end:
            qs = qs.filter(recorded_at__gte=timezone.now() - timedelta(days=30))

        buckets = {}
        for record in qs.order_by("recorded_at").iterator(chunk_size=500):
            recorded = record.recorded_at
            if granularity == "hour":
                key = recorded.replace(minute=0, second=0, microsecond=0)
            elif granularity == "month":
                key = recorded.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:  # day
                key = recorded.replace(hour=0, minute=0, second=0, microsecond=0)
            bucket_key = key.isoformat()
            entry = buckets.setdefault(
                bucket_key,
                {"bucket": bucket_key, "metrics": {}},
            )
            entry["metrics"][record.metric] = (
                entry["metrics"].get(record.metric, 0) + record.quantity
            )

        return Response(
            {
                "granularity": granularity,
                "metric": metric,
                "start": start,
                "end": end,
                "buckets": sorted(buckets.values(), key=lambda b: b["bucket"]),
            }
        )


class BillingOverviewView(APIView):
    """Combined billing dashboard payload."""

    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    required_permissions = ["billing.view"]

    def get(self, request):
        return Response(services.compute_billing_overview(request.organization))
