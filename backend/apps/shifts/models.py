from django.db import models


class ShiftPeriod(models.Model):
    """シフト期間（毎月16日〜翌月15日）"""

    start_date = models.DateField("開始日")
    end_date = models.DateField("終了日")
    request_deadline = models.DateField(
        "希望休申請締め切り",
        help_text="シフト開始15日前",
    )
    is_finalized = models.BooleanField("確定済み", default=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "shift_periods"
        verbose_name = "シフト期間"
        verbose_name_plural = "シフト期間"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.start_date} 〜 {self.end_date}"


class Shift(models.Model):
    """シフト"""

    class ShiftType(models.TextChoices):
        FULL = "full", "全日"
        MORNING = "morning", "午前"
        AFTERNOON = "afternoon", "午後"

    class LeaveType(models.TextChoices):
        PAID = "paid", "有給"
        HOLIDAY = "holiday", "公休"
        SICK = "sick", "病欠"
        OTHER = "other", "その他"

    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.CASCADE,
        related_name="shifts",
        verbose_name="スタッフ",
    )
    shift_period = models.ForeignKey(
        ShiftPeriod,
        on_delete=models.CASCADE,
        related_name="shifts",
        verbose_name="シフト期間",
    )
    date = models.DateField("日付")
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shifts",
        verbose_name="出勤店舗",
    )
    shift_type = models.CharField(
        "シフト種別",
        max_length=10,
        choices=ShiftType.choices,
        default=ShiftType.FULL,
    )
    leave_type = models.CharField(
        "休暇種別",
        max_length=20,
        choices=LeaveType.choices,
        null=True,
        blank=True,
    )
    is_confirmed = models.BooleanField("確定済み", default=False)
    is_late_request = models.BooleanField("遅延申請", default=False)
    note = models.TextField("備考", blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "shifts"
        verbose_name = "シフト"
        verbose_name_plural = "シフト"
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "date", "shift_type"],
                name="unique_staff_date_shift_type",
            )
        ]
        ordering = ["date", "staff"]

    def __str__(self):
        store_name = self.store.name if self.store else "休み"
        return f"{self.staff.name} {self.date} @ {store_name}"
