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


def validate_store_minimum_staffing(staff, date, store, shift_type, exclude_id=None):
    """所属店舗の最低薬剤師数チェック

    所属店舗の薬剤師が自店舗を離れる（休暇 or 他店配置）とき、
    残る薬剤師数が store.min_pharmacists を下回ればエラー。
    - ラウンダー（store=None）は対象外
    - 事務員は対象外（薬剤師のみカウント）
    """
    from apps.staff.models import Staff

    # Only applies to pharmacists with a home store
    if not staff.store:
        return
    if staff.role == Staff.Role.CLERK:
        return

    home_store = staff.store

    # Check if this shift takes the staff AWAY from their home store
    # (leave or assignment to a different store)
    is_leaving_home = (store is None) or (store.id != home_store.id)
    if not is_leaving_home:
        return

    # Count pharmacists working at home_store on this date
    pharmacist_roles = [Staff.Role.PHARMACIST, Staff.Role.MANAGING_PHARMACIST]
    home_staff = Staff.objects.filter(
        store=home_store,
        role__in=pharmacist_roles,
        is_active=True,
        work_status=Staff.WorkStatus.ACTIVE,
    )

    # For each home pharmacist, check if they have a shift at home_store on this date
    working_at_home = 0
    for s in home_staff:
        if s.id == staff.id:
            continue  # Exclude the staff member being scheduled

        shifts_on_date = Shift.objects.filter(staff=s, date=date)
        if exclude_id:
            shifts_on_date = shifts_on_date.exclude(id=exclude_id)

        if not shifts_on_date.exists():
            # No shift registered yet — assume they'll be at home store
            working_at_home += 1
            continue

        # Check if they have a working shift at home_store
        has_home_shift = shifts_on_date.filter(
            store=home_store,
            leave_type__isnull=True,
        ).exists()
        if has_home_shift:
            working_at_home += 1

    if working_at_home < home_store.min_pharmacists:
        raise ValidationError(
            f"{home_store.name}の{date}の薬剤師数が最低必要数（{home_store.min_pharmacists}名）を"
            f"下回ります（残り{working_at_home}名）"
        )


def validate_monthly_working_days(staff, date, shift_period, leave_type, exclude_id=None):
    """月間出勤日数の上限チェック

    出勤日数（休暇を除く、日単位でカウント）が
    staff.effective_monthly_working_days に達していればエラー。
    - 休暇シフト追加時はスキップ
    - 午前+午後の分割は1日としてカウント
    """
    # Skip check for leave shifts
    if leave_type:
        return

    max_days = staff.effective_monthly_working_days

    # Count distinct working dates in this shift period (excluding leave)
    working_shifts = Shift.objects.filter(
        staff=staff,
        shift_period=shift_period,
        leave_type__isnull=True,
    )
    if exclude_id:
        working_shifts = working_shifts.exclude(id=exclude_id)

    # Exclude the current date from count (we're about to add it)
    working_dates = set(
        working_shifts.exclude(date=date).values_list("date", flat=True)
    )

    # Current count + 1 (the new shift being added)
    if len(working_dates) + 1 > max_days:
        raise ValidationError(
            f"{staff.name}の月間出勤日数が上限（{max_days}日）を超えます"
            f"（現在{len(working_dates)}日 + 1 = {len(working_dates) + 1}日）"
        )
