"""
Offer ViewSets: templates, chains, offers, approvals, onboarding.
"""
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin, SoftDeleteDestroyMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.offers import services
from apps.offers.models import (
    Offer,
    OfferApprovalChain,
    OfferTemplate,
    OnboardingHandoff,
)
from apps.offers.serializers import (
    ApproveStepSerializer,
    CreateOfferSerializer,
    OfferApprovalChainSerializer,
    OfferListSerializer,
    OfferRespondSerializer,
    OfferSerializer,
    OfferTemplateSerializer,
    OnboardingHandoffSerializer,
)


class OfferFilter(filters.FilterSet):
    application = filters.UUIDFilter()
    candidate = filters.UUIDFilter()
    job = filters.UUIDFilter()
    status = filters.CharFilter()

    class Meta:
        model = Offer
        fields = ["application", "candidate", "job", "status"]


class OfferTemplateViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = OfferTemplate.objects.all()
    serializer_class = OfferTemplateSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["offers.view"],
        "POST": ["offers.create"],
        "PUT": ["offers.create"],
        "PATCH": ["offers.create"],
        "DELETE": ["offers.create"],
    }
    search_fields = ["name"]
    ordering = ["name"]
    audit_resource_type = "OfferTemplate"


class OfferApprovalChainViewSet(
    OrgQuerysetMixin, OrgCreateMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = OfferApprovalChain.objects.all()
    serializer_class = OfferApprovalChainSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["offers.view"],
        "POST": ["offers.approve"],
        "PUT": ["offers.approve"],
        "PATCH": ["offers.approve"],
        "DELETE": ["offers.approve"],
    }
    ordering = ["name"]
    audit_resource_type = "OfferApprovalChain"

    def perform_create(self, serializer):
        org = self.request.organization
        instance = serializer.save(
            organization=org,
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        if instance.is_default:
            OfferApprovalChain.objects.for_org(org).exclude(pk=instance.pk).update(is_default=False)

    def perform_update(self, serializer):
        instance = serializer.save(updated_by=self.request.user)
        if instance.is_default:
            OfferApprovalChain.objects.for_org(self.request.organization).exclude(
                pk=instance.pk
            ).update(is_default=False)


class OfferViewSet(
    OrgQuerysetMixin, SoftDeleteDestroyMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = Offer.objects.select_related(
        "application", "candidate", "job", "template", "approval_chain"
    ).prefetch_related("approvals")
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["offers.view"],
        "POST": ["offers.create"],
        "PUT": ["offers.create"],
        "PATCH": ["offers.create"],
        "DELETE": ["offers.create"],
    }
    filterset_class = OfferFilter
    search_fields = ["title", "candidate__email", "candidate__first_name", "job__title"]
    ordering = ["-created_at"]
    audit_resource_type = "Offer"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return OfferListSerializer
        return OfferSerializer

    def get_permissions(self):
        action_perms = {
            "submit_for_approval": ["offers.create"],
            "approve": ["offers.approve"],
            "send": ["offers.send"],
            "accept": ["offers.send"],
            "reject": ["offers.send"],
            "expire": ["offers.create"],
            "start_onboarding": ["offers.send"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        ser = CreateOfferSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        from apps.pipelines.models import Application

        application = (
            Application.objects.for_org(request.organization)
            .select_related("candidate", "job")
            .filter(pk=data["application_id"])
            .first()
        )
        if not application:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        template = None
        chain = None
        if data.get("template_id"):
            template = (
                OfferTemplate.objects.for_org(request.organization)
                .filter(pk=data["template_id"])
                .first()
            )
        if data.get("approval_chain_id"):
            chain = (
                OfferApprovalChain.objects.for_org(request.organization)
                .filter(pk=data["approval_chain_id"])
                .first()
            )

        body_html = data.get("body_html") or (template.body_html if template else "")
        body_text = data.get("body_text") or (template.body_text if template else "")
        currency = data.get("currency") or (template.default_currency if template else "USD")

        offer = Offer.objects.create(
            organization=request.organization,
            application=application,
            candidate=application.candidate,
            job=application.job,
            template=template,
            approval_chain=chain,
            title=data.get("title") or f"Offer — {application.job.title}",
            salary=data.get("salary"),
            salary_max=data.get("salary_max"),
            currency=currency,
            equity=data.get("equity", ""),
            bonus=data.get("bonus", ""),
            benefits=data.get("benefits") or [],
            start_date=data.get("start_date"),
            expires_at=data.get("expires_at"),
            employment_type=data.get("employment_type")
            or (template.default_employment_type if template else ""),
            work_location=data.get("work_location", ""),
            body_html=body_html,
            body_text=body_text,
            created_by=request.user,
            updated_by=request.user,
        )
        return Response(OfferSerializer(offer).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        offer = self.get_object()
        chain = None
        chain_id = request.data.get("approval_chain_id")
        if chain_id:
            chain = OfferApprovalChain.objects.for_org(request.organization).filter(pk=chain_id).first()
        offer = services.submit_for_approval(
            offer, chain=chain, actor=request.user, request=request
        )
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        offer = self.get_object()
        ser = ApproveStepSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = services.approve_step(
            offer,
            request.user,
            approved=ser.validated_data.get("approved", True),
            comment=ser.validated_data.get("comment", ""),
            actor=request.user,
            request=request,
        )
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        offer = self.get_object()
        # If still draft with no approvals needed, treat as approved path
        if offer.status != Offer.Status.DRAFT:
            offer.status = Offer.Status.APPROVED
            offer.save(update_fields=["status", "updated_at"])
        offer = services.send_offer(offer, actor=request.user, request=request)
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        ser = OfferRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = services.accept_offer(
            offer,
            note=ser.validated_data.get("note", ""),
            actor=request.user,
            request=request,
            start_onboarding=ser.validated_data.get("start_onboarding", True),
        )
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        offer = self.get_object()
        ser = OfferRespondSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = services.reject_offer(
            offer,
            note=ser.validated_data.get("note", ""),
            actor=request.user,
            request=request,
        )
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"])
    def expire(self, request, pk=None):
        offer = self.get_object()
        offer = services.expire_offer(offer, actor=request.user, request=request)
        return Response(OfferSerializer(offer).data)

    @action(detail=True, methods=["post"], url_path="start-onboarding")
    def start_onboarding(self, request, pk=None):
        offer = self.get_object()
        assignee_id = request.data.get("assignee_id")
        assignee = None
        if assignee_id:
            from django.contrib.auth import get_user_model

            assignee = get_user_model().objects.filter(pk=assignee_id).first()
        handoff = services.start_onboarding_handoff(
            offer, assignee=assignee, actor=request.user, request=request
        )
        return Response(OnboardingHandoffSerializer(handoff).data)


class OnboardingHandoffViewSet(
    OrgQuerysetMixin, OrgCreateMixin, AuditMixin, viewsets.ModelViewSet
):
    queryset = OnboardingHandoff.objects.select_related(
        "offer", "application", "candidate", "assignee"
    )
    serializer_class = OnboardingHandoffSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["offers.view"],
        "POST": ["offers.send"],
        "PUT": ["offers.send"],
        "PATCH": ["offers.create"],
        "DELETE": ["offers.create"],
    }
    filterset_fields = ["offer", "application", "status", "assignee"]
    ordering = ["-created_at"]
    audit_resource_type = "OnboardingHandoff"
    http_method_names = ["get", "patch", "head", "options"]
