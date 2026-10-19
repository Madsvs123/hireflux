"""
Serializers for jobs domain.
"""
from rest_framework import serializers

from apps.jobs.models import Job, JobApproval, JobRecruiter, JobTemplate, ScreeningQuestion


class ScreeningQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningQuestion
        fields = [
            "id",
            "job",
            "prompt",
            "question_type",
            "options",
            "is_required",
            "is_knockout",
            "knockout_answer",
            "order",
            "help_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "job", "created_at", "updated_at"]


class JobRecruiterSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = JobRecruiter
        fields = [
            "id",
            "job",
            "user",
            "user_email",
            "user_name",
            "is_primary",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "job", "created_at", "updated_at"]

    def get_user_name(self, obj):
        user = obj.user
        full = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
        return full or getattr(user, "email", str(user.pk))


class JobApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApproval
        fields = [
            "id",
            "job",
            "requested_by",
            "approver",
            "decided_by",
            "decision",
            "comment",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "job",
            "requested_by",
            "decided_by",
            "decided_at",
            "created_at",
            "updated_at",
        ]


class JobListSerializer(serializers.ModelSerializer)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    office_name = serializers.CharField(source="office.name", read_only=True, default=None)
    hiring_manager_email = serializers.EmailField(
        source="hiring_manager.email", read_only=True, default=None
    )
    recruiter_count = serializers.IntegerField(source="recruiters.count", read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "slug",
            "department",
            "department_name",
            "office",
            "office_name",
            "employment_type",
            "experience_level",
            "status",
            "salary_min",
            "salary_max",
            "currency",
            "salary_visible",
            "openings",
            "remote_policy",
            "hiring_manager",
            "hiring_manager_email",
            "published_at",
            "closes_at",
            "career_page_visible",
            "recruiter_count",
            "created_at",
            "updated_at",
        ]


class JobSerializer(serializers.ModelSerializer):
    screening_questions = ScreeningQuestionSerializer(many=True, read_only=True)
    recruiters = JobRecruiterSerializer(many=True, read_only=True)
    approvals = JobApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "slug",
            "department",
            "office",
            "employment_type",
            "experience_level",
            "status",
            "description",
            "requirements",
            "responsibilities",
            "salary_min",
            "salary_max",
            "currency",
            "salary_visible",
            "required_skills",
            "preferred_skills",
            "openings",
            "remote_policy",
            "hiring_manager",
            "published_at",
            "closes_at",
            "career_page_visible",
            "custom_fields",
            "pipeline_template",
            "screening_questions",
            "recruiters",
            "approvals",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "screening_questions",
            "recruiters",
            "approvals",
        ]

    def validate(self, attrs):
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min < salary_max:
            raise serializers.ValidationError(
                {"salary_max": "salary_max must be greater than or equal to salary_min."}
            )
        return attrs


class JobTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobTemplate
        fields = [
            "id",
            "name",
            "description",
            "title_template",
            "employment_type",
            "experience_level",
            "remote_policy",
            "description_body",
            "requirements",
            "responsibilities",
            "required_skills",
            "preferred_skills",
            "salary_min",
            "salary_max",
            "currency",
            "openings",
            "screening_questions",
            "custom_fields",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class JobLifecycleSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    approver = serializers.UUIDField(required=False, allow_null=True)
    publish = serializers.BooleanField(required=False, default=True)
    archive = serializers.BooleanField(required=False, default=False)


class CreateFromTemplateSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()
    title = serializers.CharField(required=False, allow_blank=True)
    department = serializers.UUIDField(required=False, allow_null=True)
    office = serializers.UUIDField(required=False, allow_null=True)
