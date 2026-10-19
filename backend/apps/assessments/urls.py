"""
Assessments URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.assessments.views import (
    AssessmentAssignmentViewSet,
    AssessmentQuestionViewSet,
    AssessmentTemplateViewSet,
    CandidateRatingViewSet,
    HiringCommentViewSet,
)

router = DefaultRouter()
router.register(r"assessment-templates" AssessmentTemplateViewSet, basename="assessment-template")
router.register(r"assessment-questions", AssessmentQuestionViewSet, basename="assessment-question")
router.register(r"assessment-assignments", AssessmentAssignmentViewSet, basename="assessment-assignment")
router.register(r"candidate_ratings", CandidateRatingViewSet, basename="candidate-rating")
router.register(r"hiring-comments", HiringCommentViewSet, basename="hiring-comment")

urlpatterns = [
    path("", include(router.urls)),
]
