from rest_framework import serializers

from .models import Shift, ShiftPeriod
from .validators import validate_managing_pharmacist_store, validate_no_double_booking


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

        exclude_id = self.instance.id if self.instance else None

        # ダブルブッキングチェック
        validate_no_double_booking(staff, date, shift_type, exclude_id)

        # 管理薬剤師の他店出勤チェック
        if store:
            validate_managing_pharmacist_store(staff, store)

        return data


class LoadRateRequestSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
