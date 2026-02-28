from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.shifts.models import Shift
from apps.staff.models import Rounder, RounderStoreExperience

from .models import Assignment, SupportSlot


def is_same_area(rounder: Rounder, slot: SupportSlot) -> bool:
    """ラウンダーの所属店舗と応援枠店舗が同一エリアかどうか"""
    home_store = rounder.staff.store
    if not home_store or not home_store.area or not slot.store.area:
        return True  # area情報がない場合は同一エリア扱い
    return home_store.area == slot.store.area


def score_rounder(rounder: Rounder, slot: SupportSlot) -> Decimal:
    """候補者スコアリング（高いほど優先）"""
    score = Decimal("0")

    # 経験済み店舗：最優先
    experienced_store_ids = set(
        RounderStoreExperience.objects.filter(
            rounder=rounder
        ).values_list("store_id", flat=True)
    )
    if slot.store_id in experienced_store_ids:
        score += 100

    # 直近3ヶ月以内の入店経験
    three_months_ago = timezone.now().date() - timedelta(days=90)
    recent = RounderStoreExperience.objects.filter(
        rounder=rounder,
        store_id=slot.store_id,
        last_visit_date__gte=three_months_ago,
    ).exists()
    if recent:
        score += 50

    # HRの余裕（実効難易度との差）
    if slot.effective_difficulty_hr:
        margin = rounder.hunter_rank - slot.effective_difficulty_hr
        score += min(margin * 2, Decimal("20"))

    # 同一エリアボーナス（近距離優先）
    if is_same_area(rounder, slot):
        score += 15

    return score


def check_assignment_prerequisites(rounder: Rounder, slot: SupportSlot) -> list[str]:
    """アサイン前提条件チェック。違反がある場合はエラーメッセージのリストを返す。"""
    errors = []

    # HR値チェック
    if slot.required_hr and rounder.hunter_rank < slot.required_hr:
        errors.append(
            f"HR値が不足しています（必要: {slot.required_hr}, 現在: {rounder.hunter_rank}）"
        )

    # 対象日に希望休・有休・他のアサインがないかチェック
    has_shift = Shift.objects.filter(
        staff=rounder.staff,
        date=slot.date,
    ).exists()
    if has_shift:
        errors.append(f"{slot.date}に既にシフトが登録されています")

    has_assignment = Assignment.objects.filter(
        rounder=rounder,
        slot__date=slot.date,
        status__in=["candidate", "confirmed"],
    ).exclude(slot=slot).exists()
    if has_assignment:
        errors.append(f"{slot.date}に既に他のアサインがあります")

    # 一人薬剤師対応チェック
    if slot.solo_hours > 0 and not rounder.can_work_alone:
        errors.append("一人薬剤師対応不可のラウンダーです")

    # 長距離移動チェック（エリア間移動を長距離と判定）
    if not is_same_area(rounder, slot) and not rounder.can_long_distance:
        errors.append("長距離移動不可のラウンダーですが、異なるエリアの店舗です")

    return errors


def generate_assignment_candidates(slot: SupportSlot, limit: int = 5) -> list[dict]:
    """応援枠に対する候補者リストをスコア順に生成"""
    rounders = Rounder.objects.filter(
        staff__is_active=True,
        staff__is_rounder=True,
    ).select_related("staff")

    candidates = []
    for rounder in rounders:
        errors = check_assignment_prerequisites(rounder, slot)
        if errors:
            continue

        candidate_score = score_rounder(rounder, slot)
        candidates.append({
            "rounder": rounder,
            "score": candidate_score,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:limit]
