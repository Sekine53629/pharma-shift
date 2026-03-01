from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT auth
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # App APIs
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/stores/", include("apps.stores.urls")),
    path("api/staff/", include("apps.staff.urls")),
    path("api/shifts/", include("apps.shifts.urls")),
    path("api/assignments/", include("apps.assignments.urls")),
    path("api/hr/", include("apps.hr_system.urls")),
    path("api/leave/", include("apps.leave.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/staffing/", include("apps.staffing.urls")),
]
