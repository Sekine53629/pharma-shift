from decimal import Decimal

from rest_framework import serializers

from .models import DailyScheduleOverride, StaffingAdjustment, StoreWeeklySchedule


# ── StoreWeeklySchedule ──────────────────────────────────────


class StoreWeeklyScheduleSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    day_of_week_display = serializers.CharField(
        source="get_day_of_week_display", read_only=True
    )

    class Meta:
        model = StoreWeeklySchedule
        fields = [
            "id",
            "store",
            "store_name",
            "day_of_week",
            "day_of_week_display",
            "is_open",
            "open_time",
            "close_time",
            "staffing_delta",
            "note",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_by", "created_at", "updated_at"]


class WeeklyScheduleItemSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    is_open = serializers.BooleanField()
    open_time = serializers.TimeField(required=False, allow_null=True, default=None)
    close_time = serializers.TimeField(required=False, allow_null=True, default=None)
    staffing_delta = serializers.DecimalField(
        max_digits=3, decimal_places=1, default=Decimal("0.0")
    )
    note = serializers.CharField(required=False, default="", allow_blank=True)


class WeeklyScheduleBulkUpsertSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    operates_on_holidays = serializers.BooleanField(required=False, default=None)
    schedules = WeeklyScheduleItemSerializer(many=True)

    def validate_schedules(self, value):
        if not value:
            raise serializers.ValidationError("schedules must not be empty.")
        for item in value:
            d = item["staffing_delta"]
            if d < Decimal("-5.0") or d > Decimal("5.0"):
                raise serializers.ValidationError(
                    f"staffing_delta must be between -5.0 and 5.0 (got {d})."
                )
        return value


# ── DailyScheduleOverride ────────────────────────────────────


class DailyScheduleOverrideSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = DailyScheduleOverride
        fields = [
            "id",
            "store",
            "store_name",
            "date",
            "is_open",
            "note",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_by", "created_at", "updated_at"]


class DailyOverrideBulkUpsertSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    overrides = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )

    def validate_overrides(self, value):
        for item in value:
            if "date" not in item or "is_open" not in item:
                raise serializers.ValidationError(
                    "Each override must have 'date' and 'is_open'."
                )
        return value


# ── StaffingAdjustment ───────────────────────────────────────


class StaffingAdjustmentSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    min_pharmacists = serializers.IntegerField(source="store.min_pharmacists", read_only=True)

    class Meta:
        model = StaffingAdjustment
        fields = [
            "id",
            "store",
            "store_name",
            "shift_period",
            "date",
            "delta",
            "source",
            "note",
            "min_pharmacists",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_by", "created_at", "updated_at"]


class BulkUpsertItemSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    date = serializers.DateField()
    delta = serializers.DecimalField(max_digits=3, decimal_places=1)
    source = serializers.ChoiceField(
        choices=StaffingAdjustment.Source.choices,
        required=False,
        default=StaffingAdjustment.Source.MANUAL,
    )
    note = serializers.CharField(required=False, default="", allow_blank=True)


class BulkUpsertSerializer(serializers.Serializer):
    shift_period = serializers.IntegerField()
    adjustments = BulkUpsertItemSerializer(many=True)

    def validate_adjustments(self, value):
        if not value:
            raise serializers.ValidationError("adjustments must not be empty.")
        for item in value:
            d = item["delta"]
            if d < Decimal("-5.0") or d > Decimal("5.0"):
                raise serializers.ValidationError(
                    f"delta must be between -5.0 and 5.0 (got {d})."
                )
        return value
