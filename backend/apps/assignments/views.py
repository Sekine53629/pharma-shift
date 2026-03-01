from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsStoreManager, IsSupervisor
from apps.shifts.models import Shift, ShiftPeriod
from apps.stores.models import Store

from .models import Assignment, AssignmentLog, SupportSlot
from .serializers import (
    AssignmentLogSerializer,
    AssignmentSerializer,
    GenerateCandidatesSerializer,
    SupportSlotSerializer,
)
from .services import create_assignment_log, generate_assignment_candidates

# 祝日マスタ (将来的にはDB管理)
from datetime import date as _date
_HOLIDAYS = {_date(2026, 3, 20)}
_DEFAULT_DAILY_RX = 150


class SupportSlotViewSet(viewsets.ModelViewSet):
    """応援枠CRUD"""

    queryset = SupportSlot.objects.select_related("store", "shift_period").all()
    serializer_class = SupportSlotSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["store", "shift_period", "priority", "is_filled", "date"]
    ordering_fields = ["priority", "date", "effective_difficulty_hr"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(store=user.staff_profile.store)
        return qs.none()

    @action(detail=False, methods=["post"], url_path="auto_generate")
    def auto_generate(self, request):
        """シフト期間の薬剤師不足日に応援枠を一括自動生成"""
        period_id = request.data.get("shift_period")
        daily_rx = int(request.data.get("daily_rx", _DEFAULT_DAILY_RX))

        if not period_id:
            return Response(
                {"detail": "shift_period is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            period = ShiftPeriod.objects.get(pk=period_id)
        except ShiftPeriod.DoesNotExist:
            return Response(
                {"detail": "ShiftPeriod not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 対象店舗: この期間にシフトがある店舗
        store_ids = (
            Shift.objects.filter(
                shift_period=period, store__isnull=False, leave_type__isnull=True
            )
            .values_list("store_id", flat=True)
            .distinct()
        )
        stores = Store.objects.filter(id__in=store_ids, is_active=True)

        # シフトindex: (store_id, date) -> pharmacist count & chief flag
        shifts = Shift.objects.filter(
            shift_period=period, store__isnull=False, leave_type__isnull=True
        ).select_related("staff")

        store_date_info: dict[tuple, dict] = {}
        for s in shifts:
            key = (s.store_id, s.date)
            if key not in store_date_info:
                store_date_info[key] = {"ph": 0, "chief": False}
            if s.staff.role in ("pharmacist", "managing_pharmacist"):
                store_date_info[key]["ph"] += 1
            if s.staff.role == "managing_pharmacist":
                store_date_info[key]["chief"] = True

        created_slots = []
        cur = period.start_date
        while cur <= period.end_date:
            is_closed = cur.weekday() == 6 or cur in _HOLIDAYS
            if is_closed:
                cur += timedelta(days=1)
                continue

            is_saturday = cur.weekday() == 5

            for store in stores:
                info = store_date_info.get((store.id, cur), {"ph": 0, "chief": False})
                shortage = store.min_pharmacists - info["ph"]
                if shortage <= 0:
                    continue

                # Skip if slot already exists
                if SupportSlot.objects.filter(
                    store=store, shift_period=period, date=cur
                ).exists():
                    continue

                # Forecast
                rx_pp = daily_rx / max(info["ph"] + 1, 1)
                if rx_pp >= 50:
                    forecast = "A"
                elif rx_pp >= 38:
                    forecast = "B"
                elif rx_pp >= 30:
                    forecast = "C"
                elif rx_pp >= 25:
                    forecast = "D"
                else:
                    forecast = "E"

                # Priority
                priority = 1 if shortage >= 3 else (2 if shortage >= 2 else 3)

                # Solo hours
                max_h = Decimal("4") if is_saturday else Decimal("8")
                if info["ph"] == 0:
                    solo = max_h
                elif info["ph"] == 1:
                    solo = Decimal("2")
                else:
                    solo = Decimal("0")

                slot = SupportSlot.objects.create(
                    store=store,
                    shift_period=period,
                    date=cur,
                    priority=priority,
                    base_difficulty=store.base_difficulty,
                    attending_pharmacists=info["ph"],
                    attending_clerks=0,
                    has_chief_present=info["chief"],
                    solo_hours=solo,
                    prescription_forecast=forecast,
                    is_filled=False,
                    note=f"[auto] 薬剤師不足 {info['ph']}/{store.min_pharmacists} (不足{shortage}名)",
                )
                created_slots.append(slot)

            cur += timedelta(days=1)

        serializer = SupportSlotSerializer(created_slots, many=True)
        return Response(
            {"created": len(created_slots), "slots": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def generate_candidates(self, request, pk=None):
        """応援枠に対する候補者リストを自動生成"""
        slot = self.get_object()
        serializer = GenerateCandidatesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidates = generate_assignment_candidates(
            slot, limit=serializer.validated_data.get("limit", 5)
        )

        result = []
        for c in candidates:
            # Assignment候補を作成
            assignment = Assignment.objects.create(
                rounder=c["rounder"],
                slot=slot,
                status=Assignment.Status.CANDIDATE,
                score=c["score"],
            )
            result.append(AssignmentSerializer(assignment).data)

        return Response(result, status=status.HTTP_201_CREATED)


class AssignmentViewSet(viewsets.ModelViewSet):
    """アサインCRUD"""

    queryset = Assignment.objects.select_related(
        "rounder__staff", "slot__store", "confirmed_by"
    ).all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["rounder", "slot", "status"]
    ordering_fields = ["score", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(slot__store=user.staff_profile.store)
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(rounder__staff=user.staff_profile)
        return qs.none()

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """アサインを確定"""
        assignment = self.get_object()
        old_status = assignment.status

        assignment.status = Assignment.Status.CONFIRMED
        assignment.confirmed_by = request.user.staff_profile
        assignment.confirmed_at = timezone.now()
        assignment.save()

        # 応援枠を充足済みにする
        assignment.slot.is_filled = True
        assignment.slot.save()

        changed_by = getattr(request.user, "staff_profile", None)
        create_assignment_log(
            assignment=assignment,
            from_status=old_status,
            to_status=Assignment.Status.CONFIRMED,
            changed_by=changed_by,
            send_notification=True,
            notification_message=(
                f"【応援確定】{assignment.slot.date} "
                f"{assignment.rounder.staff.name}が応援に入ります"
            ),
        )

        return Response(AssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """アサインを却下"""
        assignment = self.get_object()
        old_status = assignment.status

        assignment.status = Assignment.Status.REJECTED
        assignment.save()

        changed_by = getattr(request.user, "staff_profile", None)
        create_assignment_log(
            assignment=assignment,
            from_status=old_status,
            to_status=Assignment.Status.REJECTED,
            changed_by=changed_by,
        )

        return Response(AssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """確定済みアサインを取り消し"""
        assignment = self.get_object()

        if assignment.status != Assignment.Status.CONFIRMED:
            return Response(
                {"detail": "確定済みのアサインのみ取り消せます"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = assignment.status
        assignment.status = Assignment.Status.CANCELLED
        assignment.save()

        # 応援枠を未充足に戻す
        assignment.slot.is_filled = False
        assignment.slot.save()

        changed_by = getattr(request.user, "staff_profile", None)
        create_assignment_log(
            assignment=assignment,
            from_status=old_status,
            to_status=Assignment.Status.CANCELLED,
            changed_by=changed_by,
            send_notification=True,
            notification_message=(
                f"【応援取消】{assignment.slot.date} "
                f"{assignment.rounder.staff.name}の応援が取り消されました"
            ),
        )

        return Response(AssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def hand_over(self, request, pk=None):
        """確定済みアサインを別のラウンダーに引き継ぎ"""
        assignment = self.get_object()

        if assignment.status != Assignment.Status.CONFIRMED:
            return Response(
                {"detail": "確定済みのアサインのみ引き継ぎできます"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_rounder_id = request.data.get("new_rounder_id")
        if not new_rounder_id:
            return Response(
                {"detail": "new_rounder_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.staff.models import Rounder

        try:
            new_rounder = Rounder.objects.select_related("staff").get(pk=new_rounder_id)
        except Rounder.DoesNotExist:
            return Response(
                {"detail": "指定されたラウンダーが見つかりません"},
                status=status.HTTP_404_NOT_FOUND,
            )

        changed_by = getattr(request.user, "staff_profile", None)

        # 旧アサインをhanded_overに変更
        old_status = assignment.status
        assignment.status = Assignment.Status.HANDED_OVER
        assignment.save()

        create_assignment_log(
            assignment=assignment,
            from_status=old_status,
            to_status=Assignment.Status.HANDED_OVER,
            changed_by=changed_by,
            send_notification=True,
            notification_message=(
                f"【応援引継ぎ】{assignment.slot.date} "
                f"{assignment.rounder.staff.name}→{new_rounder.staff.name}に変更"
            ),
        )

        # 新アサインをconfirmedで作成
        new_assignment = Assignment.objects.create(
            rounder=new_rounder,
            slot=assignment.slot,
            status=Assignment.Status.CONFIRMED,
            confirmed_by=changed_by,
            confirmed_at=timezone.now(),
            score=assignment.score,
        )

        create_assignment_log(
            assignment=new_assignment,
            from_status="",
            to_status=Assignment.Status.CONFIRMED,
            changed_by=changed_by,
            send_notification=True,
            notification_message=(
                f"【応援確定（引継ぎ）】{new_assignment.slot.date} "
                f"{new_rounder.staff.name}が応援に入ります"
            ),
        )

        return Response(
            {
                "old_assignment": AssignmentSerializer(assignment).data,
                "new_assignment": AssignmentSerializer(new_assignment).data,
            }
        )


class AssignmentLogViewSet(viewsets.ReadOnlyModelViewSet):
    """アサイン証跡（読み取り専用）"""

    queryset = AssignmentLog.objects.select_related(
        "assignment__rounder__staff",
        "assignment__slot__store",
        "changed_by",
        "notification_log",
    ).all()
    serializer_class = AssignmentLogSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["assignment", "to_status", "notification_sent"]
    ordering_fields = ["created_at"]
