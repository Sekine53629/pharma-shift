from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


DAY_OF_WEEK_CHOICES = [
    (0, "月曜"),
    (1, "火曜"),
    (2, "水曜"),
    (3, "木曜"),
    (4, "金曜"),
    (5, "土曜"),
    (6, "日曜"),
]


class StoreWeeklySchedule(models.Model):
    """店舗ごと曜日別営業設定（営業日・営業時間・人工調整）"""

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="weekly_schedules",
        verbose_name="店舗",
    )
    day_of_week = models.IntegerField(
        "曜日",
        choices=DAY_OF_WEEK_CHOICES,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
    )
    is_open = models.BooleanField("営業", default=True)
    open_time = models.TimeField("開店時間", null=True, blank=True)
    close_time = models.TimeField("閉店時間", null=True, blank=True)
    staffing_delta = models.DecimalField(
        "人工調整",
        max_digits=3,
        decimal_places=1,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("-5.0")), MaxValueValidator(Decimal("5.0"))],
    )
    note = models.TextField("備考", blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="最終更新者",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "store_weekly_schedules"
        verbose_name = "曜日別営業設定"
        verbose_name_plural = "曜日別営業設定"
        ordering = ["store", "day_of_week"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "day_of_week"],
                name="unique_store_day_of_week",
            )
        ]

    def __str__(self):
        status = "営業" if self.is_open else "休業"
        return f"{self.store} {self.get_day_of_week_display()} {status}"


class DailyScheduleOverride(models.Model):
    """日次営業日オーバーライド（当番薬局・臨時休業等）"""

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="daily_overrides",
        verbose_name="店舗",
    )
    date = models.DateField("日付")
    is_open = models.BooleanField(
        "営業",
        help_text="True=臨時営業, False=臨時休業",
    )
    note = models.TextField("備考", blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="最終更新者",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "daily_schedule_overrides"
        verbose_name = "日次営業オーバーライド"
        verbose_name_plural = "日次営業オーバーライド"
        ordering = ["store", "date"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "date"],
                name="unique_store_date_override",
            )
        ]

    def __str__(self):
        status = "臨時営業" if self.is_open else "臨時休業"
        return f"{self.store} {self.date} {status}"


class StaffingAdjustment(models.Model):
    """店舗ごと日次の手動人工調整"""

    class Source(models.TextChoices):
        MANUAL = "manual", "手動"
        MODEL = "model", "モデル予測"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="staffing_adjustments",
        verbose_name="店舗",
    )
    shift_period = models.ForeignKey(
        "shifts.ShiftPeriod",
        on_delete=models.CASCADE,
        related_name="staffing_adjustments",
        verbose_name="シフト期間",
    )
    date = models.DateField("日付")
    delta = models.DecimalField(
        "調整値",
        max_digits=3,
        decimal_places=1,
        default=Decimal("0.0"),
        validators=[MinValueValidator(Decimal("-5.0")), MaxValueValidator(Decimal("5.0"))],
    )
    source = models.CharField(
        "ソース",
        max_length=10,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    note = models.TextField("備考", blank=True, default="")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="最終更新者",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "staffing_adjustments"
        verbose_name = "人工調整"
        verbose_name_plural = "人工調整"
        ordering = ["store", "date"]
        constraints = [
            models.UniqueConstraint(
                fields=["store", "shift_period", "date", "source"],
                name="unique_store_period_date_source",
            )
        ]

    def __str__(self):
        return f"{self.store} {self.date} delta={self.delta}"
