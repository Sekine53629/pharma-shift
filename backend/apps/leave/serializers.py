from rest_framework import serializers

from .models import LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.name", read_only=True)
    reviewer_name = serializers.CharField(source="reviewer.name", read_only=True, default=None)
    leave_type_display = serializers.CharField(source="get_leave_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "staff",
            "staff_name",
            "date",
            "leave_type",
            "leave_type_display",
            "reason",
            "status",
            "status_display",
            "reviewer",
            "reviewer_name",
            "review_comment",
            "is_late",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeaveReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["approved", "rejected"])
    review_comment = serializers.CharField(required=True, min_length=1)
