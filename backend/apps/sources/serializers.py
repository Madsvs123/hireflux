"""
Serializers for sources domain.
"""
from rest_framework import serializers

from apps.sources.models import (
    CampaignRecipient,
    CandidateSourceAttribution,
    SourceChannel,
    SourcingCampaign,
)


class SourceChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceChannel
        fields = [
            "id",
            "organization",
            "name",
            "channel_type",
            "url",
            "cost_per_post",
            "is_active",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class SourcingCampaignSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True, default=None)
    talent_pool_name = serializers.CharField(
        source="talent_pool.name", read_only=True, default=None
    )
    recipient_count = serializers.IntegerField(
        source="recipients.count", read_only=True
    )

    class Meta:
        model = SourcingCampaign
        fields = [
            "id",
            "organization",
            "name",
            "channel",
            "channel_name",
            "job",
            "job_title",
            "talent_pool",
            "talent_pool_name",
            "goal",
            "status",
            "started_at",
            "ended_at",
            "budget",
            "recipient_count",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "channel_name",
            "job_title",
            "talent_pool_name",
            "recipient_count",
            "status",
            "started_at",
            "ended_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class CampaignRecipientSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True, default=None
    )
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = CampaignRecipient
        fields = [
            "id",
            "organization",
            "campaign",
            "campaign_name",
            "candidate",
            "candidate_name",
            "email",
            "status",
            "sent_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "campaign_name",
            "candidate_name",
            "status",
            "sent_at",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class CandidateSourceAttributionSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(
        source="candidate.full_name", read_only=True
    )
    channel_name = serializers.CharField(source="channel.name", read_only=True)
    campaign_name = serializers.CharField(
        source="campaign.name", read_only=True, default=None
    )

    class Meta:
        model = CandidateSourceAttribution
        fields = [
            "id",
            "organization",
            "candidate",
            "candidate_name",
            "channel",
            "channel_name",
            "campaign",
            "campaign_name",
            "source_detail",
            "attribution_date",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "candidate_name",
            "channel_name",
            "campaign_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]


class SendRecipientsSerializer(serializers.Serializer):
    campaign = serializers.UUIDField()
    force = serializers.BooleanField(required=False, default=False)
