from rest_framework import serializers

from .models import Shift, ShiftPeriod
from .validators import (
    validate_managing_pharmacist_store,
    validate_monthly_working_days,
    validate_no_double_booking,
    validate_store_minimum_staffing,
)


class ShiftPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftPeriod
        fields = [
            "id",
            "start_date",
            "end_date",
            "request_deadline",
            "is_finalized",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ShiftSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.name", read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True, default=None)

    class Meta:
        model = Shift
        fields = [
            "id",
            "staff",
            "staff_name",
            "shift_period",
            "date",
            "store",
            "store_name",
            "shift_type",
            "leave_type",
            "is_confirmed",
            "is_late_request",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        staff = data.get("staff", getattr(self.instance, "staff", None))
        date = data.get("date", getattr(self.instance, "date", None))
        shift_type = data.get("shift_type", getattr(self.instance, "shift_type", None))
        store = data.get("store", getattr(self.instance, "store", None))
        shift_period = data.get("shift_period", getattr(self.instance, "shift_period", None))
        leave_type = data.get("leave_type", getattr(self.instance, "leave_type", None))

        exclude_id = self.instance.id if self.instance else None

        # ダブルブッキングチェック
        validate_no_double_booking(staff, date, shift_type, exclude_id)

        # 管理薬剤師の他店出勤チェック
        if store:
            validate_managing_pharmacist_store(staff, store)

        # 最低薬剤師数チェック
        validate_store_minimum_staffing(staff, date, store, shift_type, exclude_id)

        # 月間出勤日数チェック
        if shift_period:
            validate_monthly_working_days(staff, date, shift_period, leave_type, exclude_id)

        return data


class LoadRateRequestSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
