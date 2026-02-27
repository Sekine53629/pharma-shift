import csv
import io

from rest_framework import serializers

from .models import PrescriptionForecast, PrescriptionRecord


class PrescriptionRecordSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = PrescriptionRecord
        fields = [
            "id",
            "store",
            "store_name",
            "date",
            "count",
            "source",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PrescriptionForecastSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = PrescriptionForecast
        fields = [
            "id",
            "store",
            "store_name",
            "date",
            "predicted_count",
            "lower_bound",
            "upper_bound",
            "model_version",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CsvUploadSerializer(serializers.Serializer):
    """CSVアップロード用（フォールバック）"""

    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith(".csv"):
            raise serializers.ValidationError("CSVファイルのみアップロード可能です")
        return value
