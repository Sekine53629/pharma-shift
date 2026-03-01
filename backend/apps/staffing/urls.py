from rest_framework.routers import DefaultRouter

from .views import (
    DailyScheduleOverrideViewSet,
    StaffingAdjustmentViewSet,
    StoreWeeklyScheduleViewSet,
)

router = DefaultRouter()
router.register("adjustments", StaffingAdjustmentViewSet)
router.register("weekly-schedules", StoreWeeklyScheduleViewSet)
router.register("daily-overrides", DailyScheduleOverrideViewSet)

urlpatterns = router.urls
