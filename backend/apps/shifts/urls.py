from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ShiftPeriodViewSet, ShiftViewSet

router = DefaultRouter()
router.register("periods", ShiftPeriodViewSet, basename="shift-period")
router.register("entries", ShiftViewSet, basename="shift")

urlpatterns = [
    path("", include(router.urls)),
]
