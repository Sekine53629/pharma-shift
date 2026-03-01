from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsStoreManager, IsSupervisor

from .models import Rounder, RounderStoreExperience, RounderUnavailability, Staff, StaffTransfer
from .serializers import (
    RounderSerializer,
    RounderStoreExperienceSerializer,
    RounderUnavailabilitySerializer,
    StaffSerializer,
    StaffTransferInputSerializer,
    StaffTransferSerializer,
)
from .services import transfer_staff


class StaffViewSet(viewsets.ModelViewSet):
    """スタッフCRUD。作成・更新・削除は管理者のみ。"""

    queryset = Staff.objects.select_related("store", "rounder_profile").all()
    serializer_class = StaffSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["role", "employment_type", "store", "is_rounder", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        # store_manager: own store only
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(store=user.staff_profile.store)
        # rounder: own record only
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(pk=user.staff_profile.pk)
        return qs.none()

    @action(detail=True, methods=["post"], url_path="transfer", permission_classes=[IsSupervisor])
    def transfer(self, request, pk=None):
        """スタッフの所属店舗を異動する"""
        staff_obj = self.get_object()
        serializer = StaffTransferInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_store = serializer.validated_data["to_store"]
        reason = serializer.validated_data.get("reason", "")

        # 管理薬剤師は未所属にできない
        if staff_obj.role == Staff.Role.MANAGING_PHARMACIST and to_store is None:
            return Response(
                {"detail": "管理薬剤師を未所属にすることはできません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transfer_record = transfer_staff(staff_obj, to_store, request.user, reason)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        staff_obj.refresh_from_db()
        return Response({
            "staff": StaffSerializer(staff_obj).data,
            "transfer": StaffTransferSerializer(transfer_record).data,
        })


class StaffTransferLogViewSet(viewsets.ReadOnlyModelViewSet):
    """異動履歴一覧（読み取り専用）"""

    queryset = StaffTransfer.objects.select_related(
        "staff", "from_store", "to_store", "transferred_by"
    ).all()
    serializer_class = StaffTransferSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["staff", "from_store", "to_store"]
    ordering_fields = ["created_at"]


class RounderViewSet(viewsets.ModelViewSet):
    """ラウンダー詳細CRUD"""

    queryset = Rounder.objects.select_related("staff").prefetch_related(
        "store_experiences__store"
    ).all()
    serializer_class = RounderSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["can_work_alone", "has_car", "can_long_distance"]
    search_fields = ["staff__name"]
    ordering_fields = ["hunter_rank", "updated_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(staff__store=user.staff_profile.store)
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(staff=user.staff_profile)
        return qs.none()


class RounderStoreExperienceViewSet(viewsets.ModelViewSet):
    """ラウンダー経験店舗CRUD"""

    queryset = RounderStoreExperience.objects.select_related(
        "rounder__staff", "store"
    ).all()
    serializer_class = RounderStoreExperienceSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["rounder", "store"]


class BufferManagementViewSet(viewsets.ModelViewSet):
    """バッファ（ラウンダー派遣）管理"""

    queryset = Staff.objects.filter(is_active=True).select_related(
        "store", "rounder_profile"
    )
    serializer_class = StaffSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["role", "store", "is_rounder"]
    search_fields = ["name"]
    ordering_fields = ["name", "role"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(store=user.staff_profile.store)
        return qs.none()

    @action(detail=True, methods=["post"])
    def toggle_rounder(self, request, pk=None):
        """ラウンダーフラグのON/OFFを切り替え。ONの場合はRounderレコードを自動生成。"""
        staff = self.get_object()
        staff.is_rounder = not staff.is_rounder
        staff.save()

        if staff.is_rounder and not hasattr(staff, "rounder_profile"):
            Rounder.objects.create(staff=staff)
            staff.refresh_from_db()

        return Response(StaffSerializer(staff).data)

    @action(detail=True, methods=["patch"])
    def update_capabilities(self, request, pk=None):
        """ラウンダー能力をPATCH更新"""
        staff = self.get_object()

        if not staff.is_rounder:
            return Response(
                {"detail": "このスタッフはラウンダーではありません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rounder = staff.rounder_profile
        except Rounder.DoesNotExist:
            return Response(
                {"detail": "ラウンダープロフィールが見つかりません"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RounderSerializer(rounder, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        staff.refresh_from_db()
        return Response(StaffSerializer(staff).data)


class RounderUnavailabilityViewSet(viewsets.ModelViewSet):
    """ラウンダー応援不可期間CRUD"""

    queryset = RounderUnavailability.objects.select_related(
        "rounder__staff", "shift_period"
    ).all()
    serializer_class = RounderUnavailabilitySerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["rounder", "shift_period"]
