"""
Serializers for talent domain.
"""
from rest_framework import serializers

from apps.talent.models import (
    CareerPage,
    JobAlert,
    Referral,
    SavedCandidate,
    TalentPool,
    TalentPoolMember,
)


class TalentPoolSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = TalentPool
        fields = [
            "id",
            "name",
            "description",
            "tags",
            "is_active",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "member_count", "created_at", "updated_at"]

    def get_member_count(self, obj):
        return obj.members.count()


class TalentPoolMemberSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)

    class Meta:
        model = TalentPoolMember
        fields = [
            "id",
            "pool",
            "candidate",
            "candidate_name",
            "candidate_email",
            "added_by",
            "source_application",
            "created_at",
        ]
        read_only_fields = ["id", "added_by", "created_at"]


class AddToPoolSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    source_application_id = serializers.UUIDField(required=False, allow_null=True)


class ReferralSerializer(serializers.ModelSerializer):
    referrer_email = serializers.EmailField(source="referrer.email", read_only=True)

    class Meta:
        model = Referral
        fields = [
            "id",
            "referrer",
            "referrer_email",
            "candidate",
            "job",
            "application",
            "candidate_email",
            "candidate_name",
            "relationship",
            "notes",
            "status",
            "bonus_eligible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "referrer", "application", "created_at", "updated_at"]


class CreateReferralSerializer(serializers.Serializer):
    candidate_email = serializers.EmailField()
    candidate_name = serializers.CharField(required=False, allow_blank=True, default="")
    job_id = serializers.UUIDField(required=False, allow_null=True)
    relationship = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    candidate_id = serializers.UUIDField(required=False, allow_null=True)


class CareerPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerPage
        fields = [
            "id",
            "slug",
            "title",
            "tagline",
            "about",
            "branding",
            "social_links",
            "is_published",
            "custom_domain",
            "seo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublicCareerPageSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = CareerPage
        fields = [
            "slug",
            "title",
            "tagline",
            "about",
            "branding",
            "social_links",
            "organization_name",
        ]


class PublicJobSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    department = serializers.SerializerMethodField()
    office = serializers.SerializerMethodField()
    employment_type = serializers.CharField()
    experience_level = serializers.CharField()
    remote_policy = serializers.CharField()
    description = serializers.CharField()
    requirements = serializers.CharField()
    responsibilities = serializers.CharField()
    salary_min = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    salary_max = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    currency = serializers.CharField()
    salary_visible = serializers.BooleanField()
    published_at = serializers.DateTimeField(allow_null=True)

    def get_department(self, obj):
        return obj.department.name if obj.department_id else None

    def get_office(self, obj):
        return obj.office.name if obj.office_id else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.salary_visible:
            data["salary_min"] = None
            data["salary_max"] = None
        return data


class PublicApplySerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=120)
    last_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")
    cover_letter = serializers.CharField(required=False, allow_blank=True, default="")
    answers = serializers.DictField(required=False, default=dict)
    resume_text = serializers.CharField(required=False, allow_blank=True, default="")


class SavedCandidateSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)

    class Meta:
        model = SavedCandidate
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "notes",
            "folder",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = [
            "id",
            "email",
            "candidate",
            "query",
            "filters",
            "frequency",
            "is_active",
            "last_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_sent_at", "created_at", "updated_at"]
