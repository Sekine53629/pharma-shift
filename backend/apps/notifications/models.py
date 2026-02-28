from django.db import models


class NotificationLog(models.Model):
    """通知ログ（追記専用）"""

    class Trigger(models.TextChoices):
        SHIFT_CONFIRMED = "shift_confirmed", "シフト確定"
        ASSIGNMENT_GENERATED = "assignment_generated", "応援アサイン案生成"
        LEAVE_DEADLINE_SOON = "leave_deadline_soon", "希望休締め切り3日前"
        PAID_LEAVE_WARNING = "paid_leave_warning", "有休消化期限30日前"
        PAID_LEAVE_URGENT = "paid_leave_urgent", "有休消化期限7日前"
        PAID_LEAVE_OVERDUE = "paid_leave_overdue", "義務有給期限超過"
        UNFILLED_SLOT_ALERT = "unfilled_slot_alert", "充足不可アラート"
        EVALUATION_BIAS = "evaluation_bias", "不正評価検知"

    trigger = models.CharField("トリガー", max_length=50, choices=Trigger.choices)
    recipient_zoom_account = models.EmailField("送信先Zoomアカウント")
    message = models.TextField("通知内容")
    is_sent = models.BooleanField("送信済み", default=False)
    error_message = models.TextField("エラー詳細", blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "notification_logs"
        verbose_name = "通知ログ"
        verbose_name_plural = "通知ログ"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.trigger}] → {self.recipient_zoom_account} ({self.created_at})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("通知ログは更新できません（INSERT onlyポリシー）")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("通知ログは削除できません（INSERT onlyポリシー）")
