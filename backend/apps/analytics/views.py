import csv
import io

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin, IsSupervisor

from .models import PrescriptionForecast, PrescriptionRecord
from .serializers import (
    CsvUploadSerializer,
    PrescriptionForecastSerializer,
    PrescriptionRecordSerializer,
)


class PrescriptionRecordViewSet(viewsets.ModelViewSet):
    """処方実績CRUD"""

    queryset = PrescriptionRecord.objects.select_related("store").all()
    serializer_class = PrescriptionRecordSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "date", "source"]
    ordering_fields = ["date", "count"]

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAdmin],
        parser_classes=[MultiPartParser],
    )
    def upload_csv(self, request):
        """CSVファイルから処方実績を一括アップロード

        CSV形式: store_id,date,count
        """
        serializer = CsvUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        csv_file = serializer.validated_data["file"]
        decoded = csv_file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))

        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):
            try:
                PrescriptionRecord.objects.update_or_create(
                    store_id=int(row["store_id"]),
                    date=row["date"],
                    defaults={
                        "count": int(row["count"]),
                        "source": PrescriptionRecord.Source.CSV_UPLOAD,
                    },
                )
                created_count += 1
            except (KeyError, ValueError) as e:
                errors.append(f"行{row_num}: {e}")

        return Response(
            {
                "created": created_count,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED,
        )


class PrescriptionForecastViewSet(viewsets.ReadOnlyModelViewSet):
    """処方予測（読み取り専用 - バッチで生成）"""

    queryset = PrescriptionForecast.objects.select_related("store").all()
    serializer_class = PrescriptionForecastSerializer
    permission_classes = [IsSupervisor]
    filterset_fields = ["store", "date", "model_version"]
    ordering_fields = ["date", "predicted_count"]

    @action(detail=False, methods=["post"], permission_classes=[IsAdmin])
    def generate(self, request):
        """予測をオンデマンド生成（管理者専用）

        Body: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
        """
        from datetime import datetime

        from .services import generate_forecasts_lightgbm

        start_str = request.data.get("start_date")
        end_str = request.data.get("end_date")

        if not start_str or not end_str:
            return Response(
                {"detail": "start_date と end_date を指定してください"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "日付形式は YYYY-MM-DD です"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = generate_forecasts_lightgbm(start_date, end_date)
        return Response(result, status=status.HTTP_201_CREATED)
