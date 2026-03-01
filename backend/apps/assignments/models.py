from decimal import Decimal

from django.db import models


class SupportSlot(models.Model):
    """応援枠"""

    class Priority(models.IntegerChoices):
        P1 = 1, "P1: 緊急欠員・法的違反回避"
        P2 = 2, "P2: 義務有給5日消化"
        P3 = 3, "P3: 薬局長・管理薬剤師の公休確保"
        P4 = 4, "P4: 希望休・健康診断"
        P5 = 5, "P5: その他有給・任意休暇"

    class PrescriptionForecast(models.TextChoices):
        A = "A", "A（多）"
        B = "B", "B（やや多）"
        C = "C", "C（普通）"
        D = "D", "D（やや少）"
        E = "E", "E（少）"

    FORECAST_PENALTY = {
        "A": Decimal("10"),
        "B": Decimal("5"),
        "C": Decimal("0"),
        "D": Decimal("-5"),
        "E": Decimal("-10"),
    }

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="support_slots",
        verbose_name="店舗",
    )
    shift_period = models.ForeignKey(
        "shifts.ShiftPeriod",
        on_delete=models.CASCADE,
        related_name="support_slots",
        verbose_name="シフト期間",
    )
    date = models.DateField("日付")
    priority = models.IntegerField(
        "優先度",
        choices=Priority.choices,
        default=Priority.P5,
    )
    base_difficulty = models.DecimalField(
        "基本難易度",
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
    )
    attending_pharmacists = models.PositiveIntegerField("同勤薬剤師数", default=0)
    attending_clerks = models.PositiveIntegerField("同勤事務員数", default=0)
    has_chief_present = models.BooleanField("薬局長出勤", default=False)
    solo_hours = models.DecimalField(
        "一人薬剤師対応時間",
        max_digits=4,
        decimal_places=1,
        default=Decimal("0"),
    )
    prescription_forecast = models.CharField(
        "処方予測",
        max_length=1,
        choices=PrescriptionForecast.choices,
        default=PrescriptionForecast.C,
    )
    effective_difficulty_hr = models.DecimalField(
        "実効難易度（HR単位）",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
    )
    required_hr = models.DecimalField(
        "必要HR値",
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
    )
    is_filled = models.BooleanField("充足済み", default=False)
    note = models.TextField("備考", blank=True, default="")

    class Meta:
        db_table = "support_slots"
        verbose_name = "応援枠"
        verbose_name_plural = "応援枠"
        ordering = ["priority", "date"]

    def __str__(self):
        return f"[P{self.priority}] {self.store.name} {self.date}"

    def calculate_effective_difficulty(self) -> Decimal:
        """実効難易度（HR単位）を算出"""
        base = self.base_difficulty or self.store.base_difficulty
        penalty = self.FORECAST_PENALTY.get(self.prescription_forecast, Decimal("0"))

        difficulty = (
            base * 10
            - (Decimal("5") if self.has_chief_present else Decimal("0"))
            - (Decimal(str(self.attending_pharmacists)) * 3)
            + (self.solo_hours * 2)
            + penalty
        )
        return max(difficulty, Decimal("0"))

    def save(self, *args, **kwargs):
        # 保存時に実効難易度を自動算出
        self.effective_difficulty_hr = self.calculate_effective_difficulty()
        if self.required_hr is None:
            self.required_hr = self.effective_difficulty_hr
        super().save(*args, **kwargs)


class Assignment(models.Model):
    """アサイン"""

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "候補"
        CONFIRMED = "confirmed", "確定"
        REJECTED = "rejected", "却下"
        CANCELLED = "cancelled", "取消"
        HANDED_OVER = "handed_over", "引継ぎ"

    rounder = models.ForeignKey(
        "staff.Rounder",
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="ラウンダー",
    )
    slot = models.ForeignKey(
        SupportSlot,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="応援枠",
    )
    status = models.CharField(
        "ステータス",
        max_length=20,
        choices=Status.choices,
        default=Status.CANDIDATE,
    )
    confirmed_by = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_assignments",
        verbose_name="承認者",
    )
    confirmed_at = models.DateTimeField("承認日時", null=True, blank=True)
    score = models.DecimalField(
        "スコア",
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "assignments"
        verbose_name = "アサイン"
        verbose_name_plural = "アサイン"
        ordering = ["-score"]

    def __str__(self):
        return f"{self.rounder.staff.name} → {self.slot}"


class AssignmentLog(models.Model):
    """アサイン証跡（INSERT-only）"""

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="アサイン",
    )
    from_status = models.CharField(
        "変更前ステータス",
        max_length=20,
        blank=True,
        default="",
    )
    to_status = models.CharField(
        "変更後ステータス",
        max_length=20,
    )
    changed_by = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_log_actions",
        verbose_name="操作者",
    )
    notification_log = models.ForeignKey(
        "notifications.NotificationLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignment_logs",
        verbose_name="通知ログ",
    )
    notification_sent = models.BooleanField("通知送信済み", default=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "assignment_logs"
        verbose_name = "アサイン証跡"
        verbose_name_plural = "アサイン証跡"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.assignment} [{self.from_status}→{self.to_status}]"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AssignmentLog is INSERT-only. Updates are not allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AssignmentLog is INSERT-only. Deletion is not allowed.")
