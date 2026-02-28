from rest_framework import viewsets

from apps.accounts.permissions import IsAdminOrReadOnly

from .models import Store
from .serializers import StoreSerializer


class StoreViewSet(viewsets.ModelViewSet):
    """店舗マスタCRUD。作成・更新・削除は管理者のみ。"""

    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["area", "is_active"]
    search_fields = ["name", "area"]
    ordering_fields = ["name", "base_difficulty", "created_at"]
