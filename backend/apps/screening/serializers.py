"""
Serializers for screening domain.
"""
from rest_framework import serializers

from apps.screening.models import (
    CandidateJobMatch,
    ResumeParseResult,
    ScreeningRun,
    ScreeningWeightProfile,
)


class ScreeningWeightProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningWeightProfile
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "skills_weight",
            "experience_weight",
            "education_weight",
            "preferred_skills_weight",
            "keywords_weight",
            "min_recommendation_score",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        weights = [
            attrs.get("skills_weight", getattr(self.instance, "skills_weight", 0.45)),
            attrs.get("experience_weight", getattr(self.instance, "experience_weight", 0.25)),
            attrs.get("education_weight", getattr(self.instance, "education_weight", 0.10)),
            attrs.get(
                "preferred_skills_weight",
                getattr(self.instance, "preferred_skills_weight", 0.15),
            ),
            attrs.get("keywords_weight", getattr(self.instance, "keywords_weight", 0.05)),
        ]
        if any(w > 1 for w in weights):
            raise serializers.ValidationError("Weights must be non-negative.")
        return attrs


class ResumeParseResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeParseResult
        fields = [
            "id",
            "document",
            "candidate",
            "status",
            "raw_text",
            "structured",
            "error",
            "parser_version",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CandidateJobMatchSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    candidate_email = serializers.EmailField(source="candidate.email", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = CandidateJobMatch
        fields = [
            "id",
            "candidate",
            "candidate_name",
            "candidate_email",
            "job",
            "job_title",
            "application",
            "weight_profile",
            "overall_score",
            "skills_score",
            "experience_score",
            "education_score",
            "preferred_skills_score",
            "keywords_score",
            "skills_matched",
            "skills_missing",
            "preferred_matched",
            "preferred_missing",
            "experience_fit",
            "explanation",
            "is_recommendation_only",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CandidateJobMatchExplanationSerializer(serializers.ModelSerializer)
    """Focused explanation payload for UI."""

    class Meta:
        model = CandidateJobMatch
        fields = [
            "id",
            "skills_matched",
            "skills_missing",
            "preferred_matched",
            "preferred_missing",
            "experience_fit",
            "explanation",
            "is_recommendation_only",
        ]
        read_only_fields = fields


class ScreeningRunSerializer(serializers.ModelSerializer):
    match_detail = CandidateJobMatchSerializer(source="match", read_only=True)

    class Meta:
        model = ScreeningRun
        fields = [
            "id",
            "job",
            "application",
            "candidate",
            "weight_profile",
            "run_type",
            "status",
            "match",
            "match_detail",
            "result_summary",
            "error",
            "started_at",
            "completed_at",
            "triggered_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ParseResumeSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    async_mode = serializers.BooleanField(required=False, default=True)


class ScreenApplicationSerializer(serializers.Serializer):
    application_id = serializers.UUIDField(required=False)
    candidate_id = serializers.UUIDField(required=False)
    job_id = serializers.UUIDField(required=False)
    weight_profile_id = serializers.UUIDField(required=False, allow_null=True)
    async_mode = serializers.BooleanField(required=False, default=False)


class BatchScreenSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    weight_profile_id = serializers.UUIDField(required=False, allow_null=True)
    async_mode = serializers.BooleanField(required=False, default=True)


class ExtractTextSerializer(serializers.Serializer):
    text = serializers.CharField()
    extra_skills = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
