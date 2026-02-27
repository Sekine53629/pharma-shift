from decimal import Decimal

from django.db.models import Sum

from apps.staff.models import Staff

from .models import Shift


def calculate_load_rate(store_id: int, date) -> Decimal:
    """負荷率を算出

    負荷率 = 処方予測枚数 ÷ Σ(在勤薬剤師の対応上限枚数)

    負荷率 > 1.0  → 人手不足
    負荷率 0.7〜1.0 → バッファ少
    負荷率 < 0.7  → 余裕あり
    """
    # 該当日・該当店舗に出勤する薬剤師のシフトを取得
    pharmacist_shifts = Shift.objects.filter(
        store_id=store_id,
        date=date,
        staff__role__in=[
            Staff.Role.PHARMACIST,
            Staff.Role.MANAGING_PHARMACIST,
        ],
    ).select_related("staff__rounder_profile")

    if not pharmacist_shifts.exists():
        return Decimal("999.0")  # 薬剤師ゼロ = 完全な人手不足

    total_capacity = 0
    for shift in pharmacist_shifts:
        rounder_profile = getattr(shift.staff, "rounder_profile", None)
        if rounder_profile:
            total_capacity += rounder_profile.max_prescriptions
        else:
            total_capacity += 40  # デフォルト上限

    if total_capacity == 0:
        return Decimal("999.0")

    # 処方予測枚数を取得（analyticsアプリから）
    try:
        from apps.analytics.models import PrescriptionForecast

        forecast = PrescriptionForecast.objects.filter(
            store_id=store_id, date=date
        ).first()
        predicted_count = forecast.predicted_count if forecast else 30  # デフォルト
    except Exception:
        predicted_count = 30

    return Decimal(str(predicted_count)) / Decimal(str(total_capacity))


def get_store_load_rates(store_id: int, start_date, end_date) -> dict:
    """期間中の日別負荷率を取得"""
    from datetime import timedelta

    rates = {}
    current = start_date
    while current <= end_date:
        rates[current.isoformat()] = float(calculate_load_rate(store_id, current))
        current += timedelta(days=1)
    return rates
