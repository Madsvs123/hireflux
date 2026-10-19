"""
Serializers for candidates domain.
"""
from rest_framework import serializers

from apps.candidates.models import (
    Candidate,
    CandidateCertification,
    CandidateDocument,
    CandidateEducation,
    CandidateExperience,
    CandidateNote,
    CommunicationLog,
    DuplicateCandidateMatch,
)


class CandidateEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateEducation
        fields = [
            "id",
            "candidate",
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "gpa",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "candidate", "created_at", "updated_at"]


class CandidateExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateExperience
        fields = [
            "id",
            "candidate",
            "company",
            "title",
            "location",
            "start_date",
            "end_date",
            "is_current",
            "description",
            "skills_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "candidate", "created_at", "updated_at"]


class CandidateCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateCertification
        fields = [
            "id",
            "candidate",
            "name",
            "issuer",
            "issue_date",
            "expiry_date",
            "credential_id",
            "credential_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "candidate", "created_at", "updated_at"]


class CandidateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateDocument
        fields = [
            "id",
            "candidate",
            "doc_type",
            "title",
            "file",
            "file_name",
            "content_type",
            "file_size",
            "parsed_text",
            "parse_status",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "parsed_text",
            "parse_status",
            "created_at",
            "updated_at",
        ]


class CandidateNoteSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)

    class Meta:
        model = CandidateNote
        fields = [
            "id",
            "candidate",
            "body",
            "visibility",
            "pinned",
            "created_by",
            "author_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "candidate", "created_by", "created_at", "updated_at"]


class CommunicationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationLog
        fields = [
            "id",
            "candidate",
            "channel",
            "direction",
            "subject",
            "body",
            "metadata",
            "occurred_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "candidate", "created_by", "created_at", "updated_at"]


class DuplicateCandidateMatchSerializer(serializers.ModelSerializer):
    candidate_a_email = serializers.EmailField(source="candidate_a.email", read_only=True)
    candidate_b_email = serializers.EmailField(source="candidate_b.email", read_only=True)
    candidate_a_name = serializers.CharField(source="candidate_a.full_name", read_only=True)
    candidate_b_name = serializers.CharField(source="candidate_b.full_name", read_only=True)

    class Meta:
        model = DuplicateCandidateMatch
        fields = [
            "id",
            "candidate_a",
            "candidate_b",
            "candidate_a_email",
            "candidate_b_email",
            "candidate_a_name",
            "candidate_b_name",
            "match_type",
            "confidence",
            "status",
            "details",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CandidateListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "name",
            "full_name",
            "first_name",
            "last_name",
            "email",
            "phone",
            "location",
            "headline",
            "source",
            "tags",
            "skills",
            "years_experience",
            "is_talent_pool",
            "do_not_hire",
            "duplicate_of",
            "created_at",
            "updated_at",
        ]


class CandidateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    name = serializers.CharField(required=False, allow_blank=True)
    education = CandidateEducationSerializer(many=True, read_only=True)
    experience = CandidateExperienceSerializer(many=True, read_only=True)
    certifications = CandidateCertificationSerializer(many=True, read_only=True)
    documents = CandidateDocumentSerializer(many=True, read_only=True)
    notes = CandidateNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Candidate
        fields = [
            "id",
            "user",
            "name",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "location",
            "linkedin_url",
            "portfolio_url",
            "github_url",
            "website_url",
            "headline",
            "summary",
            "source",
            "tags",
            "skills",
            "years_experience",
            "salary_expectation_min",
            "salary_expectation_max",
            "salary_currency",
            "is_talent_pool",
            "do_not_hire",
            "do_not_hire_reason",
            "duplicate_of",
            "custom_fields",
            "education",
            "experience",
            "certifications",
            "documents",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "education",
            "experience",
            "certifications",
            "documents",
            "notes",
        ]

    def validate(self, attrs)
        name = attrs.pop("name", None)
        if name and attrs.get("first_name") and not (self.instance and self.instance.first_name):
            parts = name.strip().split(None, 1)
            attrs["first_name"] = parts[0]
            attrs["last_name"] = parts[1] if len(parts) > 1 else ""
        elif name and "first_name" not in attrs and self.instance is None:
            parts = name.strip().split(None, 1)
            attrs.setdefault("first_name", parts[0])
            attrs.setdefault("last_name", parts[1] if len(parts) > 1 else "")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.full_name
        return data


class DetectDuplicatesSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField(required=False, allow_null=True)
    persist = serializers.BooleanField(required=False, default=True)
    name_threshold = serializers.FloatField(required=False, default=0.85, min_value=0.5, max_value=1.0)


class MergeCandidatesSerializer(serializers.Serializer):
    primary_id = serializers.UUIDField()
    secondary_id = serializers.UUIDField()
    field_preferences = serializers.DictField(
        child=serializers.ChoiceField(choices=["primary", "secondary"]),
        required=False,
    )
