from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HrEvaluationViewSet, HrPeriodSummaryViewSet

router = DefaultRouter()
router.register("evaluations", HrEvaluationViewSet, basename="hr-evaluation")
router.register("summaries", HrPeriodSummaryViewSet, basename="hr-summary")

urlpatterns = [
    path("", include(router.urls)),
]
