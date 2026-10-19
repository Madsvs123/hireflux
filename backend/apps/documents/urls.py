"""
Documents URL routing (staff endpoints + public sign endpoints).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.documents.views import (
    DocumentCategoryViewSet,
    DocumentSignRequestViewSet,
    DocumentTemplateViewSet,
    GeneratedDocumentViewSet,
    PublicSignDetailView,
    PublicSignSubmitView,
)

router = DefaultRouter()
router.register(
    r"document-categories", DocumentCategoryViewSet, basename="document-category"
)
router.register(
    r"document-templates", DocumentTemplateViewSet, basename="document-template"
)
router.register(
    r"generated-documents", GeneratedDocumentViewSet, basename="generated-document"
)
router.register(
    r"document-sign-requests",
    DocumentSignRequestViewSet,
    basename="document-sign-request",
)

urlpatterns = [
    path("", include(router.urls)),
    path("public/sign/<uuid:token>/", PublicSignDetailView.as_view(), name="public-sign-detail"),
    path(
        "public/sign/<uuid:token>/submit/",
        PublicSignSubmitView.as_view(),
        name="public-sign-submit",
    ),
]
