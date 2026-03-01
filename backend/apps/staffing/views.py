from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsSupervisor
from apps.shifts.models import ShiftPeriod
from apps.stores.models import Store

from .models import DailyScheduleOverride, StaffingAdjustment, StoreWeeklySchedule
from .serializers import (
    BulkUpsertSerializer,
    DailyOverrideBulkUpsertSerializer,
    DailyScheduleOverrideSerializer,
    StaffingAdjustmentSerializer,
    StoreWeeklyScheduleSerializer,
    WeeklyScheduleBulkUpsertSerializer,
)


class StoreWeeklyScheduleViewSet(viewsets.ModelViewSet):
    queryset = StoreWeeklySchedule.objects.select_related("store")
    serializer_class = StoreWeeklyScheduleSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "day_of_week"]

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk_upsert")
    def bulk_upsert(self, request):
        """曜日別営業設定を一括保存（7曜日分 + 祝日営業フラグ）"""
        ser = WeeklyScheduleBulkUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        store_id = ser.validated_data["store_id"]
        items = ser.validated_data["schedules"]
        operates_on_holidays = ser.validated_data.get("operates_on_holidays")

        created = 0
        updated = 0

        with transaction.atomic():
            # Update store-level holiday flag if provided
            if operates_on_holidays is not None:
                Store.objects.filter(pk=store_id).update(
                    operates_on_holidays=operates_on_holidays
                )

            for item in items:
                _, was_created = StoreWeeklySchedule.objects.update_or_create(
                    store_id=store_id,
                    day_of_week=item["day_of_week"],
                    defaults={
                        "is_open": item["is_open"],
                        "open_time": item.get("open_time"),
                        "close_time": item.get("close_time"),
                        "staffing_delta": item["staffing_delta"],
                        "note": item.get("note", ""),
                        "updated_by": request.user,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response({"created": created, "updated": updated})


class DailyScheduleOverrideViewSet(viewsets.ModelViewSet):
    queryset = DailyScheduleOverride.objects.select_related("store")
    serializer_class = DailyScheduleOverrideSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "date", "is_open"]

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk_upsert")
    def bulk_upsert(self, request):
        """日次オーバーライドを一括保存"""
        ser = DailyOverrideBulkUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        store_id = ser.validated_data["store_id"]
        items = ser.validated_data["overrides"]

        created = 0
        updated = 0

        with transaction.atomic():
            for item in items:
                _, was_created = DailyScheduleOverride.objects.update_or_create(
                    store_id=store_id,
                    date=item["date"],
                    defaults={
                        "is_open": item["is_open"],
                        "note": item.get("note", ""),
                        "updated_by": request.user,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response({"created": created, "updated": updated})

    @action(detail=False, methods=["delete"], url_path="remove")
    def remove(self, request):
        """日次オーバーライドを削除（store_id + date）"""
        store_id = request.query_params.get("store")
        date = request.query_params.get("date")
        if not store_id or not date:
            return Response(
                {"detail": "store and date query params required."}, status=400
            )
        deleted, _ = DailyScheduleOverride.objects.filter(
            store_id=store_id, date=date
        ).delete()
        return Response({"deleted": deleted})


class StaffingAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = StaffingAdjustment.objects.select_related("store", "shift_period")
    serializer_class = StaffingAdjustmentSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "shift_period", "date", "source"]

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk_upsert")
    def bulk_upsert(self, request):
        ser = BulkUpsertSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        period_id = ser.validated_data["shift_period"]
        items = ser.validated_data["adjustments"]

        ShiftPeriod.objects.get(pk=period_id)

        created = 0
        updated = 0

        with transaction.atomic():
            for item in items:
                source = item.get("source", StaffingAdjustment.Source.MANUAL)
                _, was_created = StaffingAdjustment.objects.update_or_create(
                    store_id=item["store_id"],
                    shift_period_id=period_id,
                    date=item["date"],
                    source=source,
                    defaults={
                        "delta": item["delta"],
                        "note": item.get("note", ""),
                        "updated_by": request.user,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        return Response({"created": created, "updated": updated})
