from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NotificationLogViewSet

router = DefaultRouter()
router.register("logs", NotificationLogViewSet, basename="notification-log")

urlpatterns = [
    path("", include(router.urls)),
]
