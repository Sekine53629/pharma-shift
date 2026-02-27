from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssignmentViewSet, SupportSlotViewSet

router = DefaultRouter()
router.register("slots", SupportSlotViewSet, basename="support-slot")
router.register("entries", AssignmentViewSet, basename="assignment")

urlpatterns = [
    path("", include(router.urls)),
]
