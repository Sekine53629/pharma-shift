from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsStoreManager

from .models import HrEvaluation, HrPeriodSummary
from .serializers import (
    HrEvaluationCommentSerializer,
    HrEvaluationSerializer,
    HrPeriodSummarySerializer,
)
from .services import calculate_hr_for_period, check_evaluator_bias


class HrEvaluationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """HR評価（INSERT only - update/deleteは提供しない）"""

    queryset = HrEvaluation.objects.select_related(
        "evaluator", "rounder__staff"
    ).all()
    serializer_class = HrEvaluationSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["evaluator", "rounder", "evaluation_type", "requires_approval"]
    ordering_fields = ["created_at", "score"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(rounder__staff__store=user.staff_profile.store)
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(rounder__staff=user.staff_profile)
        return qs.none()

    @action(detail=True, methods=["post"])
    def add_comment(self, request, pk=None):
        """ラウンダー本人から異議申し立てコメントを登録

        NOTE: rounder_commentのみ更新を許可する特別な例外。
        評価レコード自体のUPDATEではなく、コメント追記として扱う。
        """
        evaluation = self.get_object()
        serializer = HrEvaluationCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # rounder_commentの追記はモデルのsave制約を迂回
        HrEvaluation.objects.filter(pk=evaluation.pk).update(
            rounder_comment=serializer.validated_data["comment"]
        )
        evaluation.refresh_from_db()
        return Response(HrEvaluationSerializer(evaluation).data)

    @action(detail=False, methods=["get"])
    def bias_check(self, request):
        """評価者バイアスチェック（管理者専用）"""
        if not request.user.has_role("admin"):
            return Response(
                {"detail": "管理者権限が必要です"},
                status=status.HTTP_403_FORBIDDEN,
            )

        evaluator_id = request.query_params.get("evaluator_id")
        if not evaluator_id:
            return Response(
                {"detail": "evaluator_idを指定してください"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = check_evaluator_bias(int(evaluator_id))
        if result:
            return Response(result)
        return Response({"alert": False})


class HrPeriodSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """HR期間サマリー（読み取り専用）"""

    queryset = HrPeriodSummary.objects.select_related("rounder__staff").all()
    serializer_class = HrPeriodSummarySerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["rounder"]
    ordering_fields = ["period_start", "computed_hr"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_any_role("admin", "supervisor"):
            return qs
        if user.has_role("store_manager") and hasattr(user, "staff_profile"):
            return qs.filter(rounder__staff__store=user.staff_profile.store)
        if user.has_role("rounder") and hasattr(user, "staff_profile"):
            return qs.filter(rounder__staff=user.staff_profile)
        return qs.none()

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def recalculate(self, request):
        """指定期間のHRを再算出"""
        rounder_id = request.data.get("rounder_id")
        period_start = request.data.get("period_start")
        period_end = request.data.get("period_end")

        if not all([rounder_id, period_start, period_end]):
            return Response(
                {"detail": "rounder_id, period_start, period_endが必要です"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.staff.models import Rounder

        rounder = Rounder.objects.get(id=rounder_id)
        summary = calculate_hr_for_period(rounder, period_start, period_end)
        return Response(HrPeriodSummarySerializer(summary).data)
