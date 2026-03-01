from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentLogViewSet, AssignmentViewSet, SupportSlotViewSet

router = DefaultRouter()
router.register("slots", SupportSlotViewSet, basename="support-slot")
router.register("entries", AssignmentViewSet, basename="assignment")
router.register("logs", AssignmentLogViewSet, basename="assignment-log")

urlpatterns = [
    path("", include(router.urls)),
]
