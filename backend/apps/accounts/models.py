from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("メールアドレスは必須です")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model with email-based authentication and role support."""

    class Role(models.TextChoices):
        ADMIN = "admin", "管理者（本部）"
        SUPERVISOR = "supervisor", "SV（エリアマネージャー）"
        STORE_MANAGER = "store_manager", "薬局長（店舗責任者）"
        ROUNDER = "rounder", "ラウンダー薬剤師"

    username = None
    email = models.EmailField("メールアドレス", unique=True)
    roles = models.JSONField(
        "権限ロール",
        default=list,
        help_text="複数ロール保持可能。例: ['admin', 'supervisor']",
    )
    is_active = models.BooleanField("有効", default=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.email

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)

    @property
    def is_admin(self) -> bool:
        return self.has_role(self.Role.ADMIN)

    @property
    def is_supervisor(self) -> bool:
        return self.has_role(self.Role.SUPERVISOR)

    @property
    def is_store_manager(self) -> bool:
        return self.has_role(self.Role.STORE_MANAGER)

    @property
    def is_rounder_user(self) -> bool:
        return self.has_role(self.Role.ROUNDER)


class AuditLog(models.Model):
    """監査ログ（追記専用 - UPDATE/DELETE禁止）"""

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="操作者",
    )
    action = models.CharField("操作種別", max_length=50)
    table_name = models.CharField("テーブル名", max_length=50, blank=True, default="")
    record_id = models.IntegerField("レコードID", null=True, blank=True)
    before_data = models.JSONField("変更前データ", null=True, blank=True)
    after_data = models.JSONField("変更後データ", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        verbose_name = "監査ログ"
        verbose_name_plural = "監査ログ"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.action}] {self.table_name}#{self.record_id} by {self.user}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("監査ログは更新できません（INSERT onlyポリシー）")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("監査ログは削除できません（INSERT onlyポリシー）")
