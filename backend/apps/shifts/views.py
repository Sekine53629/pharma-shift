from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsStoreManager

from .models import Shift, ShiftPeriod
from .serializers import LoadRateRequestSerializer, ShiftPeriodSerializer, ShiftSerializer
from .services import get_store_load_rates


class ShiftPeriodViewSet(viewsets.ModelViewSet):
    """シフト期間管理"""

    queryset = ShiftPeriod.objects.all()
    serializer_class = ShiftPeriodSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["is_finalized"]


class ShiftViewSet(viewsets.ModelViewSet):
    """シフトCRUD + ダブルブッキングチェック"""

    queryset = Shift.objects.select_related("staff", "store", "shift_period").all()
    serializer_class = ShiftSerializer
    permission_classes = [IsStoreManager]
    filterset_fields = ["staff", "store", "date", "shift_period", "shift_type", "is_confirmed"]
    search_fields = ["staff__name", "store__name"]
    ordering_fields = ["date", "staff__name"]

    @action(detail=False, methods=["post"])
    def load_rates(self, request):
        """店舗の日別負荷率を算出"""
        serializer = LoadRateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rates = get_store_load_rates(
            store_id=serializer.validated_data["store_id"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
        )
        return Response(rates, status=status.HTTP_200_OK)
