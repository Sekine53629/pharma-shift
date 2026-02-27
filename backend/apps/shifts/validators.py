from django.core.exceptions import ValidationError

from .models import Shift


def validate_no_double_booking(staff, date, shift_type, exclude_id=None):
    """ダブルブッキングチェック

    - 同一スタッフ・同一日にfullのシフトが複数 → エラー
    - morning + afternoon の組み合わせ → 許容
    - 管理薬剤師が他店のシフトに入る → エラー（別途チェック）
    """
    existing = Shift.objects.filter(staff=staff, date=date)
    if exclude_id:
        existing = existing.exclude(id=exclude_id)

    if not existing.exists():
        return

    if shift_type == Shift.ShiftType.FULL:
        # full シフトが既にある場合はエラー
        if existing.exists():
            raise ValidationError(
                f"{staff.name}は{date}に既にシフトが登録されています（全日勤務の重複）"
            )

    if shift_type in (Shift.ShiftType.MORNING, Shift.ShiftType.AFTERNOON):
        # 同じ時間帯の重複はエラー
        if existing.filter(shift_type=shift_type).exists():
            raise ValidationError(
                f"{staff.name}は{date}に既に{shift_type}シフトが登録されています"
            )
        # fullが既にある場合もエラー
        if existing.filter(shift_type=Shift.ShiftType.FULL).exists():
            raise ValidationError(
                f"{staff.name}は{date}に全日シフトが登録されています"
            )


def validate_managing_pharmacist_store(staff, store):
    """管理薬剤師が他店のシフトに入ることを防止"""
    if staff.role == "managing_pharmacist" and store and staff.store_id != store.id:
        raise ValidationError(
            f"管理薬剤師（{staff.name}）は所属店舗以外のシフトに入れません"
        )
