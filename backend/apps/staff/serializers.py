from rest_framework import serializers

from .models import Rounder, RounderStoreExperience, Staff


class RounderStoreExperienceSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = RounderStoreExperience
        fields = [
            "id",
            "rounder",
            "store",
            "store_name",
            "first_visit_date",
            "last_visit_date",
            "visit_count",
        ]
        read_only_fields = ["id"]


class RounderSerializer(serializers.ModelSerializer):
    store_experiences = RounderStoreExperienceSerializer(many=True, read_only=True)
    initial_hr = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    staff_name = serializers.CharField(source="staff.name", read_only=True)

    class Meta:
        model = Rounder
        fields = [
            "id",
            "staff",
            "staff_name",
            "hunter_rank",
            "can_work_alone",
            "max_prescriptions",
            "has_car",
            "can_long_distance",
            "managing_pharmacist_years",
            "initial_hr",
            "store_experiences",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class StaffSerializer(serializers.ModelSerializer):
    rounder_profile = RounderSerializer(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Staff
        fields = [
            "id",
            "user",
            "name",
            "role",
            "employment_type",
            "store",
            "store_name",
            "is_rounder",
            "paid_leave_deadline",
            "paid_leave_used",
            "is_active",
            "rounder_profile",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        role = data.get("role", getattr(self.instance, "role", None))
        store = data.get("store", getattr(self.instance, "store", None))
        is_rounder = data.get("is_rounder", getattr(self.instance, "is_rounder", False))

        # 管理薬剤師は店舗固定必須
        if role == Staff.Role.MANAGING_PHARMACIST and not store:
            raise serializers.ValidationError(
                {"store": "管理薬剤師は所属店舗の設定が必須です"}
            )

        # ラウンダーは所属店舗NULL
        if is_rounder and store:
            raise serializers.ValidationError(
                {"store": "ラウンダーは所属店舗をNULLにしてください（本部所属）"}
            )

        return data
