"""
Sourcing ViewSets: channels, campaigns, recipients, attribution.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import AuditMixin, OrgCreateMixin, OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser
from apps.sources import services
from apps.sources.models import (
    CampaignRecipient,
    CandidateSourceAttribution,
    SourceChannel,
    SourcingCampaign,
)
from apps.sources.serializers import (
    CampaignRecipientSerializer,
    CandidateSourceAttributionSerializer,
    SendRecipientsSerializer,
    SourceChannelSerializer,
    SourcingCampaignSerializer,
)


class SourceChannelViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SourceChannel.objects.all()
    serializer_class = SourceChannelSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["sources.view"],
        "POST": ["sources.manage"],
        "PUT": ["sources.manage"],
        "PATCH": ["sources.manage"],
        "DELETE": ["sources.manage"],
    }
    filterset_fields = ["channel_type", "is_active"]
    search_fields = ["name", "url", "notes"]
    ordering = ["name"]
    audit_resource_type = "SourceChannel"

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Aggregate campaign/recipient/attribution counts per channel."""
        return Response({"channels": services.channel_stats(request.organization)})


class SourcingCampaignViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = SourcingCampaign.objects.select_related(
        "channel", "job", "talent_pool"
    ).prefetch_related("recipients")
    serializer_class = SourcingCampaignSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["sources.view"],
        "POST": ["sources.manage"],
        "PUT": ["sources.manage"],
        "PATCH": ["sources.manage"],
        "DELETE": ["sources.manage"],
    }
    filterset_fields = ["channel", "job", "talent_pool", "status"]
    search_fields = ["name", "goal"]
    ordering = ["-created_at"]
    audit_resource_type = "SourcingCampaign"

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        campaign = self.get_object()
        campaign = services.launch_campaign(campaign, actor=request.user)
        return Response(SourcingCampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        campaign = self.get_object()
        campaign = services.pause_campaign(campaign, actor=request.user)
        return Response(SourcingCampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        campaign = self.get_object()
        campaign = services.resume_campaign(campaign, actor=request.user)
        return Response(SourcingCampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        campaign = self.get_object()
        campaign = services.complete_campaign(campaign, actor=request.user)
        return Response(SourcingCampaignSerializer(campaign).data)

    @action(detail=True, methods=["post"], url_path="sync-recipients")
    def sync_recipients(self, request, pk=None):
        """Create queued recipients from the campaign's talent pool members."""
        campaign = self.get_object()
        created = services.add_recipients_from_pool(campaign, actor=request.user)
        return Response(
            {
                "created": len(created),
                "recipient_ids": [str(r.pk) for r in created],
            }
        )


class CampaignRecipientViewSet(
    OrgQuerysetMixin,
    OrgCreateMixin,
    AuditMixin,
    viewsets.ModelViewSet,
):
    queryset = CampaignRecipient.objects.select_related("campaign", "candidate")
    serializer_class = CampaignRecipientSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {
        "SAFE": ["sources.view"],
        "POST": ["sources.manage"],
        "PUT": ["sources.manage"],
        "PATCH": ["sources.manage"],
        "DELETE": ["sources.manage"],
    }
    filterset_fields = ["campaign", "candidate", "status"]
    search_fields = ["email"]
    ordering = ["-created_at"]
    audit_resource_type = "CampaignRecipient"

    def get_permissions(self):
        action_perms = {
            "send": ["sources.view"],
            "resend": ["sources.manage"],
            "send_all": ["sources.manage"],
        }
        perms = action_perms.get(self.action)
        if perms:
            self.required_permissions = perms
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Deliver the email to a single queued recipient."""
        recipient = self.get_object()
        recipient = services.send_recipient_email(recipient, actor=request.user)
        return Response(CampaignRecipientSerializer(recipient).data)

    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        """Force re-delivery to an already-sent recipient."""
        recipient = self.get_object()
        recipient = services.send_recipient_email(
            recipient, actor=request.user, force=True
        )
        return Response(CampaignRecipientSerializer(recipient).data)

    @action(detail=False, methods=["post"], url_path="send-all")
    def send_all(self, request):
        """Queue delivery for every queued recipient of a campaign."""
        ser = SendRecipientsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.sources.models import SourcingCampaign

        campaign = (
            SourcingCampaign.objects.for_org(request.organization)
            .filter(pk=ser.validated_data["campaign_id"])
            .first()
        )
        if not campaign:
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )
        from apps.sources.tasks import send_campaign_emails

        send_campaign_emails.delay(str(campaign.pk))
        queued = services.campaign_recipients_for_send(campaign).count()
        return Response(
            {"queued": True, "campaign_id": str(campaign.pk), "pending": queued},
            status=status.HTTP_202_ACCEPTED,
        )


class CandidateSourceAttributionViewSet(
    OrgQuerysetMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = CandidateSourceAttribution.objects.select_related(
        "candidate", "channel", "campaign"
    )
    serializer_class = CandidateSourceAttributionSerializer
    permission_classes = [IsOrgMember, IsStaffUser, HasPerm]
    permission_map = {"SAFE": ["sources.view"]}
    filterset_fields = ["candidate", "channel", "campaign", "attribution_date"]
    search_fields = ["source_detail", "utm_source", "utm_medium", "utm_campaign"]
    ordering = ["-attribution_date"]

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Attributions aggregated by channel."""
        from django.utils.dateparse import parse_date

        date_from = parse_date(request.query_params.get("from") or "")
        date_to = parse_date(request.query_params.get("to") or "")
        return Response(
            services.attribution_stats(
                request.organization, date_from=date_from, date_to=date_to
            )
        )
