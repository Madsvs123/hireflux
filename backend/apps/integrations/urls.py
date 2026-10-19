"""
Integration URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.integrations.views import (
    ApiKeyViewSet,
    IntegrationConfigViewSet,
    IntegrationConnectionViewSet,
    IntegrationProviderViewSet,
    ProviderWebhookReceiver,
    WebhookDeliveryViewSet,
    WebhookEndpointViewSet,
)

router = DefaultRouter()
router.register(
    r"integration-providers", IntegrationProviderViewSet, basename="integration-provider"
)
router.register(
    r"integration-connections", IntegrationConnectionViewSet, basename="integration-connection"
)
router.register(r"integration-configs", IntegrationConfigViewSet, basename="integration-config")
router.register(r"webhook-endpoints", WebhookEndpointViewSet, basename="webhook-endpoint")
router.register(r"webhook-deliveries", WebhookDeliveryViewSet, basename="webhook-delivery")
router.register(r"api-keys", ApiKeyViewSet, basename="api-key")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "provider-webhooks/<slug:provider_key>/",
        ProviderWebhookReceiver.as_view(),
        name="provider-webhook-receiver",
    ),
]
