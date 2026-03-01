from rest_framework import serializers

from .models import Rounder, RounderStoreExperience, RounderUnavailability, Staff, StaffTransfer


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


class RounderUnavailabilitySerializer(serializers.ModelSerializer):
    rounder_name = serializers.CharField(source="rounder.staff.name", read_only=True)

    class Meta:
        model = RounderUnavailability
        fields = [
            "id",
            "rounder",
            "rounder_name",
            "shift_period",
            "reason",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RounderSerializer(serializers.ModelSerializer):
    store_experiences = RounderStoreExperienceSerializer(many=True, read_only=True)
    unavailabilities = RounderUnavailabilitySerializer(many=True, read_only=True)
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
            "unavailabilities",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class StaffSerializer(serializers.ModelSerializer):
    rounder_profile = RounderSerializer(read_only=True)
    store_name = serializers.CharField(source="store.name", read_only=True)
    effective_monthly_working_days = serializers.IntegerField(read_only=True)

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
            "monthly_working_days",
            "effective_monthly_working_days",
            "work_status",
            "is_active",
            "rounder_profile",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        role = data.get("role", getattr(self.instance, "role", None))
        store = data.get("store", getattr(self.instance, "store", None))

        # 管理薬剤師は店舗固定必須
        if role == Staff.Role.MANAGING_PHARMACIST and not store:
            raise serializers.ValidationError(
                {"store": "管理薬剤師は所属店舗の設定が必須です"}
            )

        return data


class StaffTransferInputSerializer(serializers.Serializer):
    to_store = serializers.PrimaryKeyRelatedField(
        queryset=__import__("apps.stores.models", fromlist=["Store"]).Store.objects.all(),
        allow_null=True,
    )
    reason = serializers.CharField(required=False, default="", allow_blank=True)


class StaffTransferSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.name", read_only=True)
    from_store_name = serializers.SerializerMethodField()
    to_store_name = serializers.SerializerMethodField()
    transferred_by_email = serializers.CharField(
        source="transferred_by.email", read_only=True, default=None
    )

    class Meta:
        model = StaffTransfer
        fields = [
            "id",
            "staff",
            "staff_name",
            "from_store",
            "from_store_name",
            "to_store",
            "to_store_name",
            "reason",
            "transferred_by",
            "transferred_by_email",
            "created_at",
        ]
        read_only_fields = fields

    def get_from_store_name(self, obj):
        return obj.from_store.name if obj.from_store else None

    def get_to_store_name(self, obj):
        return obj.to_store.name if obj.to_store else None
