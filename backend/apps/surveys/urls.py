"""
Surveys URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.surveys.views import (
    PublicSurveyDetailView,
    PublicSurveySubmitView,
    SurveyAnalyticsView,
    SurveyInstanceViewSet,
    SurveyInvitationViewSet,
    SurveyQuestionViewSet,
    SurveyResponseViewSet,
    SurveyTemplateViewSet,
)

router = DefaultRouter()
router.register(r"survey-templates", SurveyTemplateViewSet, basename="survey-template")
router.register(r"survey-questions", SurveyQuestionViewSet, basename="survey-question")
router.register(r"survey-instances", SurveyInstanceViewSet, basename="survey-instance")
router.register(r"survey-responses", SurveyResponseViewSet, basename="survey-response")
router.register(r"survey-invitations", SurveyInvitationViewSet, basename="survey-invitation")

urlpatterns = [
    path("", include(router.urls)),
    path("survey-analytics/", SurveyAnalyticsView.as_view(), name="survey-analytics"),
    path(
        "public/surveys/<uuid:token>/",
        PublicSurveyDetailView.as_view(),
        name="public-survey-detail",
    ),
    path(
        "public/surveys/<uuid:token>/submit/",
        PublicSurveySubmitView.as_view(),
        name="public-survey-submit",
    ),
]
