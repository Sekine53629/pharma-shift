from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count, Q

from apps.staff.models import Rounder

from .models import HrEvaluation, HrPeriodSummary


def points_to_hr(points: Decimal) -> Decimal:
    """累積ポイント → HR値変換（成長曲線）"""
    if points <= 30:
        return points * 2  # 1pt = 2HR
    elif points <= 60:
        return Decimal("60") + (points - 30) * 1  # 1pt = 1HR
    else:
        return Decimal("90") + (points - 60) * Decimal("0.5")  # 1pt = 0.5HR


def calculate_hr_for_period(rounder: Rounder, period_start, period_end) -> HrPeriodSummary:
    """指定期間のHR値を算出"""
    # 期間内の評価を集計
    evaluations = HrEvaluation.objects.filter(
        rounder=rounder,
        period_start=period_start,
        period_end=period_end,
    )

    supervisor_total = sum(
        e.score for e in evaluations if e.evaluation_type == "supervisor"
    )
    self_total = sum(
        e.score for e in evaluations if e.evaluation_type == "self"
    )

    # 前期繰越
    previous_summary = HrPeriodSummary.objects.filter(
        rounder=rounder,
        period_end__lte=period_start,
    ).order_by("-period_end").first()

    if previous_summary:
        carried_over = previous_summary.total_points * Decimal("0.7")
    else:
        # 初回は管理薬剤師経験年数から初期値を設定
        carried_over = min(
            rounder.managing_pharmacist_years * Decimal("5"),
            Decimal("30"),
        )

    total_points = carried_over + supervisor_total + self_total
    computed_hr = points_to_hr(max(total_points, Decimal("0")))

    summary, _ = HrPeriodSummary.objects.update_or_create(
        rounder=rounder,
        period_start=period_start,
        defaults={
            "period_end": period_end,
            "supervisor_total": supervisor_total,
            "self_total": self_total,
            "carried_over": carried_over,
            "total_points": total_points,
            "computed_hr": computed_hr,
        },
    )

    # Rounderのhunter_rankも更新
    rounder.hunter_rank = computed_hr
    rounder.save(update_fields=["hunter_rank"])

    return summary


def check_consecutive_negative_evaluations(evaluator_id: int, rounder_id: int) -> bool:
    """同一評価者から2クール連続 -1 かチェック"""
    recent_evals = HrEvaluation.objects.filter(
        evaluator_id=evaluator_id,
        rounder_id=rounder_id,
        evaluation_type="supervisor",
    ).order_by("-period_end")[:2]

    evals = list(recent_evals)
    if len(evals) < 2:
        return False

    return all(e.score <= Decimal("-1.0") for e in evals)


def check_evaluator_bias(evaluator_id: int) -> dict | None:
    """特定評価者の -1 比率が全体平均の2倍超かチェック"""
    # 全評価者の -1 比率の平均
    all_stats = HrEvaluation.objects.filter(
        evaluation_type="supervisor"
    ).aggregate(
        total=Count("id"),
        negative=Count("id", filter=Q(score__lte=Decimal("-1.0"))),
    )

    if not all_stats["total"]:
        return None

    avg_negative_ratio = all_stats["negative"] / all_stats["total"]

    # この評価者の -1 比率
    evaluator_stats = HrEvaluation.objects.filter(
        evaluator_id=evaluator_id,
        evaluation_type="supervisor",
    ).aggregate(
        total=Count("id"),
        negative=Count("id", filter=Q(score__lte=Decimal("-1.0"))),
    )

    if not evaluator_stats["total"] or evaluator_stats["total"] < 3:
        return None  # サンプル少なすぎ

    evaluator_ratio = evaluator_stats["negative"] / evaluator_stats["total"]

    if evaluator_ratio > avg_negative_ratio * 2:
        return {
            "evaluator_id": evaluator_id,
            "evaluator_ratio": evaluator_ratio,
            "average_ratio": avg_negative_ratio,
            "alert": True,
        }

    return None
