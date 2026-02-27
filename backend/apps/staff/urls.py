from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RounderStoreExperienceViewSet, RounderViewSet, StaffViewSet

router = DefaultRouter()
router.register("members", StaffViewSet, basename="staff")
router.register("rounders", RounderViewSet, basename="rounder")
router.register("experience", RounderStoreExperienceViewSet, basename="rounder-experience")

urlpatterns = [
    path("", include(router.urls)),
]
