from rest_framework import serializers

from .models import Assignment, SupportSlot


class SupportSlotSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = SupportSlot
        fields = [
            "id",
            "store",
            "store_name",
            "shift_period",
            "date",
            "priority",
            "priority_display",
            "base_difficulty",
            "attending_pharmacists",
            "attending_clerks",
            "has_chief_present",
            "solo_hours",
            "prescription_forecast",
            "effective_difficulty_hr",
            "required_hr",
            "is_filled",
            "note",
        ]
        read_only_fields = ["id", "effective_difficulty_hr"]


class AssignmentSerializer(serializers.ModelSerializer):
    rounder_name = serializers.CharField(source="rounder.staff.name", read_only=True)
    slot_info = SupportSlotSerializer(source="slot", read_only=True)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "rounder",
            "rounder_name",
            "slot",
            "slot_info",
            "status",
            "confirmed_by",
            "confirmed_at",
            "score",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "score"]


class GenerateCandidatesSerializer(serializers.Serializer):
    slot_id = serializers.IntegerField()
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)
