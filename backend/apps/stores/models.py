from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Store(models.Model):
    """店舗マスタ"""

    # 初見殺しフラグごとの難易度補正値
    DIFFICULTY_ADJUSTMENTS = {
        "has_controlled_medical_device": Decimal("0.5"),  # 高度管理医療機器
        "has_toxic_substances": Decimal("0.5"),  # 毒劇物販売
        "has_workers_comp": Decimal("0.3"),  # 労災対応
        "has_auto_insurance": Decimal("0.3"),  # 自賠責対応
        "has_special_public_expense": Decimal("0.4"),  # 特殊公費
        "has_local_voucher": Decimal("0.2"),  # 地方振興券対応
        "has_holiday_rules": Decimal("0.3"),  # 祝日出勤特殊ルール
    }

    name = models.CharField("店舗名", max_length=100)
    area = models.CharField("エリア区分", max_length=50, blank=True, default="")
    base_difficulty = models.DecimalField(
        "基本難易度",
        max_digits=3,
        decimal_places=1,
        default=Decimal("3.0"),
        validators=[MinValueValidator(Decimal("1.0")), MaxValueValidator(Decimal("5.0"))],
    )
    slots = models.PositiveIntegerField("応援枠数", default=1)

    # 初見殺しフラグ
    has_controlled_medical_device = models.BooleanField("高度管理医療機器", default=False)
    has_toxic_substances = models.BooleanField("毒劇物販売", default=False)
    has_workers_comp = models.BooleanField("労災対応", default=False)
    has_auto_insurance = models.BooleanField("自賠責対応", default=False)
    has_special_public_expense = models.BooleanField("特殊公費", default=False)
    has_local_voucher = models.BooleanField("地方振興券対応", default=False)
    has_holiday_rules = models.BooleanField("祝日出勤特殊ルール", default=False)

    zoom_account = models.EmailField("Zoomアカウント", max_length=200, blank=True, default="")
    is_active = models.BooleanField("有効", default=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "stores"
        verbose_name = "店舗"
        verbose_name_plural = "店舗"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def effective_difficulty(self) -> Decimal:
        """初見殺しフラグのON数に応じて基本難易度を補正した実効難易度を算出"""
        adjustment = sum(
            value
            for flag, value in self.DIFFICULTY_ADJUSTMENTS.items()
            if getattr(self, flag)
        )
        return min(self.base_difficulty + adjustment, Decimal("5.0"))

    @property
    def active_flag_count(self) -> int:
        """有効な初見殺しフラグの数"""
        return sum(
            1
            for flag in self.DIFFICULTY_ADJUSTMENTS
            if getattr(self, flag)
        )
