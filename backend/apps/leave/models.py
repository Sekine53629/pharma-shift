from django.db import models


class LeaveRequest(models.Model):
    """休暇申請"""

    class LeaveType(models.TextChoices):
        PAID = "paid", "有給"
        HOLIDAY = "holiday", "公休"
        SICK = "sick", "病欠"
        OTHER = "other", "その他"

    class Status(models.TextChoices):
        PENDING = "pending", "申請中"
        APPROVED = "approved", "承認"
        REJECTED = "rejected", "却下"

    staff = models.ForeignKey(
        "staff.Staff",
        on_delete=models.CASCADE,
        related_name="leave_requests",
        verbose_name="スタッフ",
    )
    date = models.DateField("休暇日")
    leave_type = models.CharField(
        "休暇種別",
        max_length=20,
        choices=LeaveType.choices,
    )
    reason = models.TextField("申請理由", blank=True, default="")
    status = models.CharField(
        "ステータス",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewer = models.ForeignKey(
        "staff.Staff",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests",
        verbose_name="承認者",
    )
    review_comment = models.TextField("承認/却下コメント", blank=True, default="")
    is_late = models.BooleanField(
        "締め切り後申請",
        default=False,
        help_text="シフト希望休申請締め切り後の申請",
    )
    created_at = models.DateTimeField("申請日時", auto_now_add=True)

    class Meta:
        db_table = "leave_requests"
        verbose_name = "休暇申請"
        verbose_name_plural = "休暇申請"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.staff.name} {self.date} {self.get_leave_type_display()} ({self.get_status_display()})"
