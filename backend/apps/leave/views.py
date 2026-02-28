from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsStoreManager

from .models import LeaveRequest
from .serializers import LeaveRequestSerializer, LeaveReviewSerializer
from .services import get_all_paid_leave_alerts


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """休暇申請CRUD"""

    queryset = LeaveRequest.objects.select_related("staff", "reviewer").all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["staff", "leave_type", "status", "date", "is_late"]
    search_fields = ["staff__name"]
    ordering_fields = ["date", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(staff__store=user.staff_profile.store)
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(staff=user.staff_profile)
        return qs.none()

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """休暇申請の承認/却下"""
        leave_request = self.get_object()
        serializer = LeaveReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leave_request.status = serializer.validated_data["status"]
        leave_request.review_comment = serializer.validated_data["review_comment"]
        leave_request.reviewer = request.user.staff_profile
        leave_request.save()

        # 有給承認時は消化日数を加算
        if (
            leave_request.status == LeaveRequest.Status.APPROVED
            and leave_request.leave_type == LeaveRequest.LeaveType.PAID
        ):
            staff = leave_request.staff
            staff.paid_leave_used += 1
            staff.save(update_fields=["paid_leave_used"])

        return Response(LeaveRequestSerializer(leave_request).data)

    @action(detail=False, methods=["get"])
    def paid_leave_alerts(self, request):
        """義務有給消化アラート一覧"""
        alerts = get_all_paid_leave_alerts()
        return Response(alerts, status=status.HTTP_200_OK)
