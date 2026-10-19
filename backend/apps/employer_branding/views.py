"""
Employer branding ViewSets and public careers site endpoint.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.employer_branding.models import (
    BrandProfile,
    CareerSiteConfig,
    CulturePost,
    TeamPage,
    Testimonial,
)
from apps.employer_branding.serializers import (
    BrandProfileSerializer,
    CareerSiteConfigSerializer,
    CulturePostSerializer,
    TeamPageSerializer,
    TestimonialSerializer,
)
from apps.employer_branding import services


class BrandProfileViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    """Retrieve/update the organization's single brand profile (one-to-one)."""

    queryset = BrandProfile.objects.select_related("organization")
    serializer_class = BrandProfileSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["employer_branding.view"],
        "POST": ["employer_branding.manage"],
        "PUT": ["employer_branding.manage"],
        "PATCH": ["employer_branding.manage"],
        "DELETE": ["employer_branding.manage"],
    }
    audit_resource_type = "BrandProfile"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_object(self):
        obj = self.get_queryset().first()
        if obj is None:
            raise NotFound("No brand profile for this organization.")
        return obj

    def list(self, request, *args, **kwargs):
        """One-to-one resource: return the org profile directly."""
        return self.retrieve(request)

    def perform_create(self, serializer):
        existing = self.get_queryset().first()
        if existing is not None:
            # Upsert semantics for the one-to-one resource.
            serializer.instance = existing
            self.perform_update(serializer)
            return
        super().perform_create(serializer)

    def get_permissions(self):
        action_perms = {
            "publish": ["employer_branding.manage"],
            "unpublish": ["employer_branding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def publish(self, request):
        profile = self.get_object()
        profile = services.publish_profile(profile, actor=request.user, request=request)
        return Response(BrandProfileSerializer(profile).data)

    @action(detail=False, methods=["post"])
    def unpublish(self, request):
        profile = self.get_object()
        profile = services.unpublish_profile(profile, actor=request.user, request=request)
        return Response(BrandProfileSerializer(profile).data)


class CareerSiteConfigViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    """Retrieve/update the organization's careers site config (one-to-one)."""

    queryset = CareerSiteConfig.objects.select_related("organization")
    serializer_class = CareerSiteConfigSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["employer_branding.view"],
        "POST": ["employer_branding.manage"],
        "PUT": ["employer_branding.manage"],
        "PATCH": ["employer_branding.manage"],
        "DELETE": ["employer_branding.manage"],
    }
    audit_resource_type = "CareerSiteConfig"
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_object(self):
        obj = self.get_queryset().first()
        if obj is None:
            raise NotFound("No careers site config for this organization.")
        return obj

    def list(self, request, *args, **kwargs):
        """One-to-one resource: return the org config directly."""
        return self.retrieve(request)

    def perform_create(self, serializer):
        existing = self.get_queryset().first()
        if existing is not None:
            # Upsert semantics for the one-to-one resource.
            serializer.instance = existing
            self.perform_update(serializer)
            return
        super().perform_create(serializer)

    def get_permissions(self):
        action_perms = {
            "publish": ["employer_branding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def publish(self, request):
        config = self.get_object()
        config = services.publish_career_site(config, actor=request.user, request=request)
        return Response(CareerSiteConfigSerializer(config).data)


class TeamPageViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = TeamPage.objects.all()
    serializer_class = TeamPageSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["employer_branding.view"],
        "POST": ["employer_branding.manage"],
        "PUT": ["employer_branding.manage"],
        "PATCH": ["employer_branding.manage"],
        "DELETE": ["employer_branding.manage"],
    }
    filterset_fields = ["is_active"]
    search_fields = ["name", "role", "bio"]
    ordering_fields = ["order", "name", "created_at"]
    ordering = ["order", "name"]
    audit_resource_type = "TeamPage"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs


class TestimonialViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["employer_branding.view"],
        "POST": ["employer_branding.manage"],
        "PUT": ["employer_branding.manage"],
        "PATCH": ["employer_branding.manage"],
        "DELETE": ["employer_branding.manage"],
    }
    filterset_fields = ["is_active", "rating"]
    search_fields = ["author_name", "author_role", "content"]
    ordering_fields = ["order", "rating", "created_at"]
    ordering = ["order", "created_at"]
    audit_resource_type = "Testimonial"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs


class CulturePostViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    SoftDeleteDestroyMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = CulturePost.objects.all()
    serializer_class = CulturePostSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["employer_branding.view"],
        "POST": ["employer_branding.manage"],
        "PUT": ["employer_branding.manage"],
        "PATCH": ["employer_branding.manage"],
        "DELETE": ["employer_branding.manage"],
    }
    filterset_fields = ["status", "tags"]
    search_fields = ["title", "body_html"]
    ordering_fields = ["published_at", "created_at", "title", "status"]
    ordering = ["-published_at", "-created_at"]
    audit_resource_type = "CulturePost"

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is not None:
            qs = qs.filter(organization=org)
        return qs

    def get_permissions(self):
        action_perms = {
            "publish": ["employer_branding.manage"],
            "archive": ["employer_branding.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        post = self.get_object()
        post = services.publish_culture_post(post, actor=request.user, request=request)
        return Response(CulturePostSerializer(post).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        post = self.get_object()
        post = services.archive_culture_post(post, actor=request.user, request=request)
        return Response(CulturePostSerializer(post).data)


class PublicCareersSiteView(APIView):
    """Anonymous payload for the public careers site."""

    permission_classes = []
    authentication_classes = []

    def get(self, request, slug=None):
        payload = services.get_public_careers_site(slug)
        if payload is None:
            return Response(
                {"detail": "Careers site not found or not enabled."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(payload)
