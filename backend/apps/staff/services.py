from django.db import transaction

from .models import Staff, StaffTransfer


def transfer_staff(staff: Staff, to_store, user, reason: str = "") -> StaffTransfer:
    """スタッフの所属店舗を変更し、異動履歴を記録する。

    Args:
        staff: 対象スタッフ
        to_store: 異動先店舗 (Store or None)
        user: 実行ユーザー
        reason: 異動理由

    Returns:
        StaffTransfer: 作成された異動履歴

    Raises:
        ValueError: 同一店舗への異動、または管理薬剤師の未所属化
    """
    from_store = staff.store

    # Same-store check (including both None)
    from_id = from_store.pk if from_store else None
    to_id = to_store.pk if to_store else None
    if from_id == to_id:
        raise ValueError("異動元と異動先が同じ店舗です")

    with transaction.atomic():
        transfer = StaffTransfer.objects.create(
            staff=staff,
            from_store=from_store,
            to_store=to_store,
            reason=reason,
            transferred_by=user,
        )
        staff.store = to_store
        staff.save(update_fields=["store"])

    return transfer
