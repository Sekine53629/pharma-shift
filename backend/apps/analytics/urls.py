from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PrescriptionForecastViewSet, PrescriptionRecordViewSet

router = DefaultRouter()
router.register("records", PrescriptionRecordViewSet, basename="prescription-record")
router.register("forecasts", PrescriptionForecastViewSet, basename="prescription-forecast")

urlpatterns = [
    path("", include(router.urls)),
]
