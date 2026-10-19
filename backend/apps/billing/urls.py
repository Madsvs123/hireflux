"""
Billing URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.billing.views import (
    BillingOverviewView,
    InvoiceViewSet,
    PaymentMethodViewSet,
    PaymentTransactionViewSet,
    PlanViewSet,
    SubscriptionViewSet,
    UsageViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register(r"payment-transactions", PaymentTransactionViewSet, basename="payment-transaction")
router.register(r"usage", UsageViewSet, basename="usage")

urlpatterns = [
    path("", include(router.urls)),
    path("billing-overview/", BillingOverviewView.as_view(), name="billing-overview"),
]
