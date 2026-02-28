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
