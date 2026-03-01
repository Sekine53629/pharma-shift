from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Staff(models.Model):
    """スタッフ"""

    class Role(models.TextChoices):
        PHARMACIST = "pharmacist", "薬剤師"
        CLERK = "clerk", "事務員"
        MANAGING_PHARMACIST = "managing_pharmacist", "管理薬剤師"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "正社員"
        PART_TIME = "part_time", "パート"
        DISPATCH = "dispatch", "派遣"

    class WorkStatus(models.TextChoices):
        ACTIVE = "active", "通常勤務"
        ON_LEAVE = "on_leave", "休職中"
        MATERNITY = "maternity", "産休・育休中"
        TEMPORARY = "temporary", "臨時人員"

    class PaidLeaveDeadline(models.TextChoices):
        SEPTEMBER = "09/15", "9月15日"
        FEBRUARY = "02/15", "2月15日"

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profile",
        verbose_name="ユーザーアカウント",
    )
    name = models.CharField("氏名", max_length=100)
    role = models.CharField("職種", max_length=30, choices=Role.choices)
    employment_type = models.CharField(
        "雇用形態", max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
        verbose_name="所属店舗",
    )
    is_rounder = models.BooleanField("ラウンダー", default=False)
    paid_leave_deadline = models.CharField(
        "義務有給期限区分",
        max_length=5,
        choices=PaidLeaveDeadline.choices,
        default=PaidLeaveDeadline.SEPTEMBER,
    )
    paid_leave_used = models.PositiveIntegerField("当期消化日数", default=0)
    monthly_working_days = models.PositiveIntegerField(
        "月間所定労働日数",
        null=True,
        blank=True,
        help_text="シフト期間あたりの所定労働日数（未設定時は雇用形態から自動算出）",
    )
    work_status = models.CharField(
        "稼働状況",
        max_length=20,
        choices=WorkStatus.choices,
        default=WorkStatus.ACTIVE,
    )
    is_active = models.BooleanField("有効", default=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "staff"
        verbose_name = "スタッフ"
        verbose_name_plural = "スタッフ"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    @property
    def is_auto_assignable(self) -> bool:
        return self.is_active and self.work_status == self.WorkStatus.ACTIVE

    @property
    def is_managing_pharmacist(self) -> bool:
        return self.role == self.Role.MANAGING_PHARMACIST

    @property
    def effective_monthly_working_days(self) -> int:
        """月間所定労働日数（スタッフ個別設定 > 店舗設定 > 雇用形態デフォルト）"""
        if self.monthly_working_days is not None:
            return self.monthly_working_days
        if self.store_id and self.store and self.store.monthly_working_days is not None:
            return self.store.monthly_working_days
        defaults = {
            self.EmploymentType.FULL_TIME: 22,
            self.EmploymentType.PART_TIME: 15,
            self.EmploymentType.DISPATCH: 20,
        }
        return defaults.get(self.employment_type, 22)


class Rounder(models.Model):
    """ラウンダー詳細"""

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        related_name="rounder_profile",
        verbose_name="スタッフ",
    )
    hunter_rank = models.DecimalField(
        "HR値",
        max_digits=5,
        decimal_places=1,
        default=Decimal("20.0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    can_work_alone = models.BooleanField("一人薬剤師対応可", default=False)
    max_prescriptions = models.PositiveIntegerField(
        "1日対応上限枚数",
        default=30,
        validators=[MaxValueValidator(50)],
    )
    has_car = models.BooleanField("自家用車有無", default=False)
    can_long_distance = models.BooleanField("長距離移動可", default=False)
    managing_pharmacist_years = models.DecimalField(
        "管理薬剤師経験年数",
        max_digits=4,
        decimal_places=1,
        default=Decimal("0"),
    )
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "rounders"
        verbose_name = "ラウンダー"
        verbose_name_plural = "ラウンダー"

    def __str__(self):
        return f"{self.staff.name} (HR:{self.hunter_rank})"

    @property
    def initial_hr(self) -> Decimal:
        """管理薬剤師経験年数から算出される初期HR値"""
        return min(self.managing_pharmacist_years * 5, Decimal("30"))


class RounderStoreExperience(models.Model):
    """ラウンダー経験店舗"""

    rounder = models.ForeignKey(
        Rounder,
        on_delete=models.CASCADE,
        related_name="store_experiences",
        verbose_name="ラウンダー",
    )
    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="experienced_rounders",
        verbose_name="店舗",
    )
    first_visit_date = models.DateField("初回入店日", null=True, blank=True)
    last_visit_date = models.DateField("最終入店日", null=True, blank=True)
    visit_count = models.PositiveIntegerField("入店回数", default=1)

    class Meta:
        db_table = "rounder_store_experience"
        verbose_name = "ラウンダー経験店舗"
        verbose_name_plural = "ラウンダー経験店舗"
        unique_together = [("rounder", "store")]

    def __str__(self):
        return f"{self.rounder.staff.name} → {self.store.name} ({self.visit_count}回)"


class RounderUnavailability(models.Model):
    """ラウンダー応援不可期間"""

    rounder = models.ForeignKey(
        Rounder,
        on_delete=models.CASCADE,
        related_name="unavailabilities",
        verbose_name="ラウンダー",
    )
    shift_period = models.ForeignKey(
        "shifts.ShiftPeriod",
        on_delete=models.CASCADE,
        related_name="rounder_unavailabilities",
        verbose_name="応援不可期間",
    )
    reason = models.TextField("理由", blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "rounder_unavailabilities"
        verbose_name = "ラウンダー応援不可期間"
        verbose_name_plural = "ラウンダー応援不可期間"
        unique_together = [("rounder", "shift_period")]

    def __str__(self):
        return f"{self.rounder.staff.name} - {self.shift_period}"


class StaffTransfer(models.Model):
    """異動履歴（INSERT-only）"""

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name="transfers",
        verbose_name="スタッフ",
    )
    from_store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfers_out",
        verbose_name="異動元店舗",
    )
    to_store = models.ForeignKey(
        "stores.Store",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfers_in",
        verbose_name="異動先店舗",
    )
    reason = models.TextField("理由", blank=True, default="")
    transferred_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_transfers",
        verbose_name="実行者",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "staff_transfers"
        verbose_name = "異動履歴"
        verbose_name_plural = "異動履歴"
        ordering = ["-created_at"]

    def __str__(self):
        from_name = self.from_store.name if self.from_store else "(未所属)"
        to_name = self.to_store.name if self.to_store else "(未所属)"
        return f"{self.staff.name}: {from_name} → {to_name}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("StaffTransfer is INSERT-only. Updates are not allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("StaffTransfer is INSERT-only. Deletion is not allowed.")
