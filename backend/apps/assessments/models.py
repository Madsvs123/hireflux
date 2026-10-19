"""
Assessment templates, assignments, answers, ratings, and hiring comments.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class AssessmentTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    class AssessmentType(models.TextChoices):
        SKILLS = "skills", "Skills"
        CODING = "coding", "Coding"
        PERSONALITY = "personality", "Personality"
        TAKE_HOME = "take_home", "Take Home"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    assessment_type = models.CharField(
        max_length=32,
        choices=AssessmentType.choices,
        default=AssessmentType.SKILLS,
    )
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    passing_score = models.FloatField(
        null=True,
        blank=True,
        help_text="0–100 threshold for objective scoring.",
    )
    instructions = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class AssessmentQuestion(TenantModel, AuditedModel):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
        MULTI_SELECT = "multi_select", "Multi Select"
        TRUE_FALSE = "true_false", "True/False"
        SHORT_TEXT = "short_text", "Short Text"
        LONG_TEXT = "long_text", "Long Text"
        CODING = "coding", "Coding"
        FILE_UPLOAD = "file_upload", "File Upload"

    template = models.ForeignKey(
        AssessmentTemplate, on_delete=models.CASCADE, related_name="questions"
    )
    prompt = models.TextField()
    question_type = models.CharField(
        max_length=32,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE,
    )
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="[{id, label}] for choice questions",
    )
    correct_answer = models.JSONField(
        null=True,
        blank=True,
        help_text="Objective answer payload for auto-scoring",
    )
    points = models.FloatField(default=0.0)
    is_knockout = models.BooleanField(
        default=False,
        help_text="Wrong answer fails the assignment regardless of total score.",
    )
    is_required = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [models.Index(fields=["template", "order"])]

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:60]}"


class AssessmentAssignment(TenantModel, SoftDeleteModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        SCORED = "scored", "Scored"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    template = models.ForeignKey(
        AssessmentTemplate, on_delete=models.CASCADE, related_name="assignments"
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="assessments",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    max_score = models.FloatField(null=True, blank=True)
    score_percent = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    knockout_failed = models.BooleanField(default=False)
    scoring_details = models.JSONField(default=dict, blank=True)
    access_token = models.CharField(max_length=32, blank=True, default="", db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self):
        return f"Assessment {self.template_id} → {self.candidate_id}"


class AssessmentAnswer(TenantModel, AuditedModel):
    assignment = models.ForeignKey(
        AssessmentAssignment, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        AssessmentQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    answer = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.FloatField(null=True, blank=True)
    scored_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-question__order"]
        unique_together = [("assignment", "question")]

    def __str__(self):
        return f"Answer {self.question_id} on {self.assignment_id}"


class CandidateRating(TenantModel, AuditedModel):
    """Staff rating of a candidate (optionally scoped to application)."""

    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="ratings"
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ratings",
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_ratings",
    )
    score = models.PositiveSmallIntegerField(default=5, help_text="1–5 star rating")
    dimensions = models.JSONField(default=dict, blank=True)
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "candidate", "application", "rater")]

    def __str__(self):
        return f"Rating {self.score} by {self.rater_id}"


class HiringComment(TenantModel, AuditedModel):
    """Threaded hiring discussion with @mentions."""

    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="hiring_comments",
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hiring_comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hiring_comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    body = models.TextField()
    mentions = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="mentioned_in_hiring_comments",
        blank=True,
    )
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author_id} on {self.candidate_id}"
