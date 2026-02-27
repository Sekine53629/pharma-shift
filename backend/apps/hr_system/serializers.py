from decimal import Decimal

from rest_framework import serializers

from .models import HrEvaluation, HrPeriodSummary
from .services import check_consecutive_negative_evaluations


class HrEvaluationSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source="evaluator.name", read_only=True)
    rounder_name = serializers.CharField(source="rounder.staff.name", read_only=True)

    class Meta:
        model = HrEvaluation
        fields = [
            "id",
            "evaluator",
            "evaluator_name",
            "rounder",
            "rounder_name",
            "period_start",
            "period_end",
            "score",
            "evaluation_type",
            "reason",
            "rounder_comment",
            "requires_approval",
            "created_at",
        ]
        read_only_fields = ["id", "requires_approval", "created_at"]

    def validate_score(self, value):
        eval_type = self.initial_data.get("evaluation_type", "supervisor")
        if eval_type == "supervisor":
            if value < Decimal("-1.0") or value > Decimal("1.0"):
                raise serializers.ValidationError("応援担当評価は-1.0〜+1.0の範囲です")
        elif eval_type == "self":
            if value < Decimal("-0.5") or value > Decimal("0.5"):
                raise serializers.ValidationError("自己評価は-0.5〜+0.5の範囲です")
        return value

    def create(self, validated_data):
        # 連続-1チェック
        if (
            validated_data.get("score") <= Decimal("-1.0")
            and validated_data.get("evaluation_type") == "supervisor"
        ):
            if check_consecutive_negative_evaluations(
                validated_data["evaluator"].id,
                validated_data["rounder"].id,
            ):
                validated_data["requires_approval"] = True

        return super().create(validated_data)


class HrEvaluationCommentSerializer(serializers.Serializer):
    """ラウンダー本人の異議申し立てコメント用"""

    comment = serializers.CharField(max_length=1000)


class HrPeriodSummarySerializer(serializers.ModelSerializer):
    rounder_name = serializers.CharField(source="rounder.staff.name", read_only=True)

    class Meta:
        model = HrPeriodSummary
        fields = [
            "id",
            "rounder",
            "rounder_name",
            "period_start",
            "period_end",
            "supervisor_total",
            "self_total",
            "carried_over",
            "total_points",
            "computed_hr",
            "created_at",
        ]
        read_only_fields = "__all__"
