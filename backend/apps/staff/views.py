from rest_framework import viewsets

from apps.accounts.permissions import IsAdmin, IsSupervisor

from .models import Rounder, RounderStoreExperience, Staff
from .serializers import RounderSerializer, RounderStoreExperienceSerializer, StaffSerializer


class StaffViewSet(viewsets.ModelViewSet):
    """スタッフCRUD。作成・更新・削除は管理者のみ。"""

    queryset = Staff.objects.select_related("store", "rounder_profile").all()
    serializer_class = StaffSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["role", "employment_type", "store", "is_rounder", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]


class RounderViewSet(viewsets.ModelViewSet):
    """ラウンダー詳細CRUD"""

    queryset = Rounder.objects.select_related("staff").prefetch_related(
        "store_experiences__store"
    ).all()
    serializer_class = RounderSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["can_work_alone", "has_car", "can_long_distance"]
    search_fields = ["staff__name"]
    ordering_fields = ["hunter_rank", "updated_at"]


class RounderStoreExperienceViewSet(viewsets.ModelViewSet):
    """ラウンダー経験店舗CRUD"""

    queryset = RounderStoreExperience.objects.select_related(
        "rounder__staff", "store"
    ).all()
    serializer_class = RounderStoreExperienceSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["rounder", "store"]
