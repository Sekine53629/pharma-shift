from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """管理者（本部）のみ許可"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_role("admin")


class IsSupervisor(BasePermission):
    """SV（エリアマネージャー）以上を許可"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_any_role(
            "admin", "supervisor"
        )


class IsStoreManager(BasePermission):
    """薬局長以上を許可"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_any_role(
            "admin", "supervisor", "store_manager"
        )


class IsRounder(BasePermission):
    """ラウンダー薬剤師を許可"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_role("rounder")


class IsAdminOrReadOnly(BasePermission):
    """管理者は全操作可、その他は読み取りのみ"""

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.has_role("admin")
