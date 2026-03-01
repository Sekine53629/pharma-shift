from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BufferManagementViewSet,
    RounderStoreExperienceViewSet,
    RounderUnavailabilityViewSet,
    RounderViewSet,
    StaffTransferLogViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register("members", StaffViewSet, basename="staff")
router.register("rounders", RounderViewSet, basename="rounder")
router.register("experience", RounderStoreExperienceViewSet, basename="rounder-experience")
router.register("buffer", BufferManagementViewSet, basename="buffer")
router.register("transfers", StaffTransferLogViewSet, basename="staff-transfer")
router.register("unavailabilities", RounderUnavailabilityViewSet, basename="rounder-unavailability")

urlpatterns = [
    path("", include(router.urls)),
]
