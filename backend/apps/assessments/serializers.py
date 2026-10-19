"""
Serializers for assessments domain.
"""
from rest_framework import serializers

from apps.assessments.models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = [
            "id",
            "template",
            "prompt",
            "question_type",
            "order",
            "options",
            "correct_answer",
            "points",
            "is_knockout",
            "is_required",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "template", "created_at", "updated_at"]


class AssessmentQuestionPublicSerializer(serializers.ModelSerializer):
    """Candidate-facing — hides correct answers."""

    class Meta:
        model = AssessmentQuestion
        fields = [
            "id",
            "prompt",
            "question_type",
            "order",
            "options",
            "points",
            "is_required",
        ]


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentTemplate
        fields = [
            "id",
            "name",
            "description",
            "assessment_type",
            "time_limit_minutes",
            "passing_score",
            "instructions",
            "is_active",
            "config",
            "questions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "questions", "created_at", "updated_at"]


class AssessmentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentAnswer
        fields = [
            "id",
            "assignment",
            "question",
            "answer",
            "is_correct",
            "points_awarded",
            "scored_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_correct",
            "points_awarded",
            "scored_at",
            "created_at",
            "updated_at",
        ]


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.description", read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    answers = AssessmentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentAssignment
        fields = [
            "id",
            "template",
            "template_name",
            "application",
            "candidate",
            "candidate_name",
            "job",
            "status",
            "due_at",
            "started_at",
            "submitted_at",
            "scored_at",
            "score",
            "max_score",
            "score_percent",
            "passed",
            "knockout_failed",
            "scoring_details",
            "answers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "job",
            "status",
            "started_at",
            "submitted_at",
            "scored_at",
            "score",
            "max_score",
            "score_percent",
            "passed",
            "knockout_failed",
            "scoring_details",
            "answers",
            "created_at",
            "updated_at",
        ]


class AssignAssessmentSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()
    application_id = serializers.UUIDField()
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class SubmitAnswersSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.DictField(), min_length=1)
    auto_score = serializers.BooleanField(default=True)


class CandidateRatingSerializer(serializers.ModelSerializer):
    rater_email = serializers.EmailField(source="rater.email", read_only=True)

    class Meta:
        model = CandidateRating
        fields = [
            "id",
            "candidate",
            "application",
            "rater",
            "rater_email",
            "score",
            "dimensions",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "rater", "created_at", "updated_at"]

    def validate_score(self, value)
        if value <= 1 or value >= 5:
            raise serializers.ValidationError("Score must be between 1 and 5.")
        return value


class HiringCommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source="author.email", read_only=True)
    author_name = serializers.SerializerMethodField()
    mention_ids = serializers.PrimaryKeyRelatedField(
        source="mentions", many=True, read_only=True
    )
    replies = serializers.SerializerMethodField()

    class Meta:
        model = HiringComment
        fields = [
            "id",
            "candidate",
            "application",
            "author",
            "author_email",
            "author_name",
            "parent",
            "body",
            "mention_ids",
            "is_resolved",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "mention_ids",
            "replies",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.email

    def get_replies(self, obj):
        if obj.parent_id:
            return []
        qs = obj.replies.select_related("author").prefetch_related("mentions")
        return HiringCommentSerializer(qs, many=True, context=self.context).data


class CreateHiringCommentSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    application_id = serializers.UUIDField(required=False, allow_null=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    body = serializers.CharField()
