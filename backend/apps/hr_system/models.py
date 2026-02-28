from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class HrEvaluation(models.Model):
    """HR評価（INSERT only - UPDATE/DELETE禁止）"""

    evaluator = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="given_evaluations",
        verbose_name="評価者",
    )
    rounder = models.ForeignKey(
        "staff.Rounder",
        on_delete=models.PROTECT,
        related_name="evaluations",
        verbose_name="被評価者",
    )
    period_start = models.DateField("評価期間開始")
    period_end = models.DateField("評価期間終了")
    score = models.DecimalField(
        "評価スコア",
        max_digits=3,
        decimal_places=1,
        validators=[
            MinValueValidator(Decimal("-1.0")),
            MaxValueValidator(Decimal("1.0")),
        ],
    )
    evaluation_type = models.CharField(
        "評価種別",
        max_length=20,
        choices=[
            ("supervisor", "応援担当評価"),
            ("self", "自己評価"),
        ],
        default="supervisor",
    )
    reason = models.TextField("評価理由")
    rounder_comment = models.TextField("本人異議コメント", blank=True, default="")
    requires_approval = models.BooleanField(
        "上位承認必要",
        default=False,
        help_text="同一評価者から2クール連続-1の場合にTrue",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "hr_evaluations"
        verbose_name = "HR評価"
        verbose_name_plural = "HR評価"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.evaluator.name} → {self.rounder.staff.name}: "
            f"{self.score} ({self.period_start}〜{self.period_end})"
        )

    def clean(self):
        super().clean()
        if self.evaluation_type == "self":
            if self.score < Decimal("-0.5") or self.score > Decimal("0.5"):
                raise ValidationError(
                    {"score": "自己評価は-0.5〜+0.5の範囲です"}
                )

    def save(self, *args, **kwargs):
        # UPDATE禁止：既存レコードのsave（pkがある場合）はエラー
        if self.pk:
            raise ValueError("HR評価レコードは更新できません（INSERT onlyポリシー）")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("HR評価レコードは削除できません（INSERT onlyポリシー）")


class HrPeriodSummary(models.Model):
    """HR期間サマリー（半年クールごとの累積ポイント）"""

    rounder = models.ForeignKey(
        "staff.Rounder",
        on_delete=models.CASCADE,
        related_name="hr_summaries",
        verbose_name="ラウンダー",
    )
    period_start = models.DateField("期間開始")
    period_end = models.DateField("期間終了")
    supervisor_total = models.DecimalField(
        "応援担当評価合計",
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
    )
    self_total = models.DecimalField(
        "自己評価合計",
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
    )
    carried_over = models.DecimalField(
        "前期繰越ポイント",
        max_digits=5,
        decimal_places=1,
        default=Decimal("0"),
    )
    total_points = models.DecimalField(
        "累積ポイント",
        max_digits=6,
        decimal_places=1,
        default=Decimal("0"),
    )
    computed_hr = models.DecimalField(
        "算出HR値",
        max_digits=5,
        decimal_places=1,
        default=Decimal("20"),
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "hr_period_summaries"
        verbose_name = "HR期間サマリー"
        verbose_name_plural = "HR期間サマリー"
        unique_together = [("rounder", "period_start")]
        ordering = ["-period_start"]

    def __str__(self):
        return f"{self.rounder.staff.name} HR:{self.computed_hr} ({self.period_start})"
