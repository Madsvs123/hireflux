"""
Survey models: templates, questions, instances, responses, invitations.
"""
import uuid

from django.db import models

from apps.core.models import AuditedModel, SoftDeleteManager, SoftDeleteModel, TenantModel


class SurveyTemplate(TenantModel, SoftDeleteModel, AuditedModel):
    """A reusable survey definition (candidate experience, onboarding, EEO...)."""

    class SurveyType(models.TextChoices):
        CANDIDATE_EXPERIENCE = "candidate_experience", "Candidate Experience"
        ONBOARDING = "onboarding", "Onboarding"
        EEO = "eeo", "EEO"
        INTERNAL = "internal", "Internal"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    survey_type = models.CharField(
        max_length=32,
        choices=SurveyType.choices,
        default=SurveyType.CANDIDATE_EXPERIENCE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    thank_you_message = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name


class SurveyQuestion(TenantModel, SoftDeleteModel, AuditedModel):
    """A single question inside a survey template."""

    class QuestionType(models.TextChoices):
        RATING = "rating", "Rating"
        TEXT = "text", "Text"
        CHOICE = "choice", "Choice"
        BOOLEAN = "boolean", "Boolean"

    template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.CASCADE,
        related_name="questions",
        db_index=True,
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=16,
        choices=QuestionType.choices,
        default=QuestionType.TEXT,
    )
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Choices for 'choice' questions; scale labels for 'rating'",
    )
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["template", "order", "created_at"]
        unique_together = [("organization", "template", "question_text")]

    def __str__(self):
        return f"{self.template_id}: {self.question_text[:60]}"


class SurveyInstance(TenantModel, SoftDeleteModel, AuditedModel):
    """A single survey sent to one candidate/context."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIALLY_COMPLETED = "partially_completed", "Partially Completed"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"

    template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.CASCADE,
        related_name="instances",
        db_index=True,
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_instances",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_instances",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    token = models.UUIDField(
        default=uuid.uuid4(),
        unique=True,
        editable=False,
        db_index=True,
        help_text="Public submission token for the anonymous survey link",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    anonymous = models.BooleanField(default=False)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "template", "-created_at"]),
            models.Index(fields=["organization", "status", "-created_at"]),
        ]

    def __str__(self):
        return f"SurveyInstance {self.template_id} [{self.status}]"


class SurveyResponse(TenantModel, SoftDeleteModel, AuditedModel):
    """Answer to one question within an instance."""

    instance = models.ForeignKey(
        SurveyInstance,
        on_delete=models.CASCADE,
        related_name="responses",
        db_index=True,
    )
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name="responses",
        db_index=True,
    )
    answer = models.JSONField(
        default=dict,
        help_text="Structured answer, e.g. {'rating': 4} or {'text': '...'}",
    )
    answered_at = models.DateTimeField(auto_now_add=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-answered_at"]
        unique_together = [("organization", "instance", "question")]

    def __str__(self):
        return f"Response {self.question_id} on instance {self.instance_id}"


class SurveyInvitation(TenantModel, SoftDeleteModel, AuditedModel):
    """Email invitation for an instance."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        OPENED = "opened", "Opened"
        COMPLETED = "completed", "Completed"

    instance = models.ForeignKey(
        SurveyInstance,
        on_delete=models.CASCADE,
        related_name="invitations",
        db_index=True,
    )
    email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("organization", "instance", "email")]

    def __str__(self):
        return f"{self.email} [{self.status}]"
