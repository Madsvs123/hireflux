"""
Serializers for offers domain.
"""
from rest_framework import serializers

from apps.offers.models import (
    Offer,
    OfferApproval,
    OfferApprovalChain,
    OfferTemplate,
    OnboardingHandoff,
)


class OfferTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferTemplate
        fields = [
            "id",
            "name",
            "description",
            "body_html",
            "body_text",
            "default_currency",
            "default_employment_type",
            "variables",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OfferApprovalChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferApprovalChain
        fields = [
            "id",
            "name",
            "description",
            "steps",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OfferApprovalSerializer(serializers.ModelSerializer):
    approver_email = serializers.EmailField(source="approver.email", read_only=True)

    class Meta:
        model = OfferApproval
        fields = [
            "id",
            "offer",
            "step_order",
            "approver",
            "approver_email",
            "status",
            "label",
            "comment",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class OnboardingHandoffSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)

    class Meta:
        model = OnboardingHandoff
        fields = [
            "id",
            "offer",
            "application",
            "candidate",
            "candidate_name",
            "status",
            "start_date",
            "checklist",
            "assignee",
            "notes",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "offer", "application", "candidate", "created_at", "updated_at"]


class OfferListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "application",
            "candidate",
            "candidate_name",
            "job",
            "job_title",
            "status",
            "title",
            "salary",
            "currency",
            "start_date",
            "sent_at",
            "created_at",
        ]


class OfferSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    approvals = OfferApprovalSerializer(many=True, read_only=True)
    onboarding_handoff = OnboardingHandoffSerializer(many=True, read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "application",
            "candidate",
            "candidate_name",
            "job",
            "job_title",
            "template",
            "approval_chain",
            "status",
            "title",
            "salary",
            "salary_max",
            "currency",
            "equity",
            "bonus",
            "benefits",
            "start_date",
            "expires_at",
            "employment_type",
            "work_location",
            "body_html",
            "body_text",
            "current_approval_step",
            "sent_at",
            "responded_at",
            "candidate_response_note",
            "metadata",
            "approvals",
            "onboarding_handoff",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "job",
            "current_approval_step",
            "sent_at",
            "responded_at",
            "candidate_response_note",
            "approvals",
            "onboarding_handoff",
            "created_at",
            "updated_at",
        ]


class CreateOfferSerializer(serializers.Serializer):
    application_id = serializers.UUIDField()
    template_id = serializers.UUIDField(required=False, allow_null=True)
    approval_chain_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    currency = serializers.CharField(required=False, default="USD")
    equity = serializers.CharField(required=False, allow_blank=True, default="")
    bonus = serializers.CharField(required=False, allow_blank=True, default="")
    benefits = serializers.ListField(required=False, default=list)
    start_date = serializers.DateField(required=False, allow_null=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    employment_type = serializers.CharField(required=False, allow_blank=True, default="")
    work_location = serializers.CharField(required=False, allow_blank=True, default="")
    body_html = serializers.CharField(required=False, allow_blank=True, default="")
    body_text = serializers.CharField(required=False, allow_blank=True, default="")


class ApproveStepSerializer(serializers.Serializer):
    approved = serializers.BooleanField(default=True)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class OfferRespondSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
    start_onboarding = serializers.BooleanField(default=True)
