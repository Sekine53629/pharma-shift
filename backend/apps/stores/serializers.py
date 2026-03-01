from rest_framework import serializers

from .models import Store


class StoreSerializer(serializers.ModelSerializer):
    effective_difficulty = serializers.DecimalField(
        max_digits=3, decimal_places=1, read_only=True
    )
    active_flag_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Store
        fields = [
            "id",
            "name",
            "area",
            "base_difficulty",
            "effective_difficulty",
            "slots",
            "min_pharmacists",
            "has_controlled_medical_device",
            "has_toxic_substances",
            "has_workers_comp",
            "has_auto_insurance",
            "has_special_public_expense",
            "has_local_voucher",
            "has_holiday_rules",
            "active_flag_count",
            "monthly_working_days",
            "operates_on_holidays",
            "zoom_account",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
