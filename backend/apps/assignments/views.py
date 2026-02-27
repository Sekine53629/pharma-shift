from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsSupervisor

from .models import Assignment, SupportSlot
from .serializers import (
    AssignmentSerializer,
    GenerateCandidatesSerializer,
    SupportSlotSerializer,
)
from .services import generate_assignment_candidates


class SupportSlotViewSet(viewsets.ModelViewSet):
    """応援枠CRUD"""

    queryset = SupportSlot.objects.select_related("store", "shift_period").all()
    serializer_class = SupportSlotSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "shift_period", "priority", "is_filled", "date"]
    ordering_fields = ["priority", "date", "effective_difficulty_hr"]

    @action(detail=True, methods=["post"])
    def generate_candidates(self, request, pk=None):
        """応援枠に対する候補者リストを自動生成"""
        slot = self.get_object()
        serializer = GenerateCandidatesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidates = generate_assignment_candidates(
            slot, limit=serializer.validated_data.get("limit", 5)
        )

        result = []
        for c in candidates:
            # Assignment候補を作成
            assignment = Assignment.objects.create(
                rounder=c["rounder"],
                slot=slot,
                status=Assignment.Status.CANDIDATE,
                score=c["score"],
            )
            result.append(AssignmentSerializer(assignment).data)

        return Response(result, status=status.HTTP_201_CREATED)


class AssignmentViewSet(viewsets.ModelViewSet):
    """アサインCRUD"""

    queryset = Assignment.objects.select_related(
        "rounder__staff", "slot__store", "confirmed_by"
    ).all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["rounder", "slot", "status"]
    ordering_fields = ["score", "created_at"]

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """アサインを確定"""
        assignment = self.get_object()
        assignment.status = Assignment.Status.CONFIRMED
        assignment.confirmed_by = request.user.staff_profile
        assignment.confirmed_at = timezone.now()
        assignment.save()

        # 応援枠を充足済みにする
        assignment.slot.is_filled = True
        assignment.slot.save()

        return Response(AssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """アサインを却下"""
        assignment = self.get_object()
        assignment.status = Assignment.Status.REJECTED
        assignment.save()
        return Response(AssignmentSerializer(assignment).data)
