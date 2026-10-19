"""
Advisory NLP screening models — never auto-hire.
"""
from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, TenantModel


class ScreeningWeightProfile(TenantModel, AuditedModel):
    """
    Weighted scoring profile for candidate↔job matching.
    Weights should sum roughly to 1.0 but are normalized at score time.
    """

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    skills_weight = models.FloatField(default=0.45)
    experience_weight = models.FloatField(default=0.35)
    education_weight = models.FloatField(default=0.10)
    preferred_skills_weight = models.FloatField(default=0.15)
    keywords_weight = models.FloatField(default=0.05)
    min_recommendation_score = models.FloatField(
        default=0.6,
        help_text="Advisory threshold only — never triggers auto-hire.",
    )
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("organization", "name")]

    def __str__(self):
        return self.name

    def normalized_weights(self) -> dict:
        raw = {
            "skills": self.skills_weight,
            "experience": self.experience_weight,
            "education": self.education_weight,
            "preferred_skills": self.preferred_skills_weight,
            "keywords": self.keywords_weight,
        }
        total = sum(max(0.0, v) for v in raw.values()) or 1.0
        return {k: max(0.0, v) / total for k, v in raw.items()}


class ResumeParseResult(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(
        "candidates.CandidateDocument",
        on_delete=models.CASCADE,
        related_name="parse_results",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="resume_parses",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    raw_text = models.TextField(blank=True, default="")
    structured = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extracted skills, experience, education, contact, keywords",
    )
    error = models.TextField(blank=True, default="")
    parser_version = models.CharField(max_length=32, default="heuristic-v1")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Parse {self.status} for doc {self.document_id}"


class CandidateJobMatch(TenantModel, AuditedModel):
    """
    Explainable candidate↔job match score.

    CRITICAL: is_recommendation_only is ALWAYS True.
    Scores are advisory and must never auto-hire or auto-reject.
    """

    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="job_matches"
    )
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="candidate_matches")
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches",
    )
    weight_profile = models.ForeignKey(
        ScreeningWeightProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches",
    )
    overall_score = models.FloatField(default=0.0, db_index=True)
    skills_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=0.0)
    education_score = models.FloatField(default=0.0)
    preferred_skills_score = models.FloatField(default=0.0)
    keywords_score = models.FloatField(default=0.0)
    skills_matched = models.JSONField(default=list, blank=True)
    skills_missing = models.JSONField(default=list, blank=True)
    preferred_matched = models.JSONField(default=list, blank=True)
    preferred_missing = models.JSONField(default=list, blank=True)
    experience_fit = models.JSONField(default=dict, blank=True)
    explanation = models.JSONField(default=dict, blank=True)
    is_recommendation_only = models.BooleanField(
        default=True,
        editable=False,
        help_text="Always True. Screening is advisory and never auto-hires.",
    )

    class Meta:
        ordering = ["overall_score"]
        indexes = [
            models.Index(fields=["organization", "job", "-overall_score"]),
            models.Index(fields=["organization", "candidate", "-overall_score"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_recommendation_only=True),
                name="candidate_job_match_recommendation_only",
            )
        ]

    def save(self, *args, **kwargs)
        self.is_recommendation_only = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Match {self.overall_score:.2f}: {self.candidate_id} ↔ {self.job_id}"


class ScreeningRun(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class RunType(models.TextChoices):
        SINGLE = "single", "Single Application"
        BATCH_JOB = "batch_job", "Batch Job"
        PARSE = "parse", "Resume Parse"
        RERUN = "rerun", "Re-run"

    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, null=True, blank=True, related_name="screening_runs"
    )
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="screening_runs",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="screening_runs",
    )
    weight_profile = models.ForeignKey(
        ScreeningWeightProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    run_type = models.CharField(max_length=16, choices=RunType.choices, default=RunType.SINGLE)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    match = models.ForeignKey(
        CandidateJobMatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    result_summary = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="screening_runs_triggered",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScreeningRun {self.run_type} [{self.status}]"
