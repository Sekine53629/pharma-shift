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
    def is_managing_pharmacist(self) -> bool:
        return self.role == self.Role.MANAGING_PHARMACIST


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
