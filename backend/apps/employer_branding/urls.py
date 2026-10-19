"""
Employer branding URL routing.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.employer_branding.views import (
    BrandProfileViewSet,
    CareerSiteConfigViewSet,
    CulturePostViewSet,
    PublicCareersSiteView,
    TeamPageViewSet,
    TestimonialViewSet,
)

router = DefaultRouter()
router.register(r"brand-profile", BrandProfileViewSet, basename="brand-profile")
router.register(r"career-site-config", CareerSiteConfigViewSet, basename="career-site-config")
router.register(r"team-pages", TeamPageViewSet, basename="team-page")
router.register(r"testimonials", TestimonialViewSet, basename="testimonial")
router.register(r"culture-posts", CulturePostViewSet, basename="culture-post")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public-careers-site/<slug:slug>/",
        PublicCareersSiteView.as_view(),
        name="public-careers-site",
    ),
]
