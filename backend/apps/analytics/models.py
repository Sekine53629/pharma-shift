from django.db import models


class PrescriptionRecord(models.Model):
    """処方実績（Musubiスクレイピング結果）"""

    class Source(models.TextChoices):
        SCRAPING = "scraping", "スクレイピング"
        CSV_UPLOAD = "csv_upload", "CSVアップロード"

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="prescription_records",
        verbose_name="店舗",
    )
    date = models.DateField("日付")
    count = models.PositiveIntegerField("処方枚数")
    source = models.CharField(
        "データソース",
        max_length=20,
        choices=Source.choices,
        default=Source.SCRAPING,
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "prescription_records"
        verbose_name = "処方実績"
        verbose_name_plural = "処方実績"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "date"],
                name="unique_store_date_prescription",
            )
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.store.name} {self.date}: {self.count}枚"


class PrescriptionForecast(models.Model):
    """処方予測（LightGBM出力）"""

    store = models.ForeignKey(
        "stores.Store",
        on_delete=models.CASCADE,
        related_name="prescription_forecasts",
        verbose_name="店舗",
    )
    date = models.DateField("日付")
    predicted_count = models.PositiveIntegerField("予測枚数")
    lower_bound = models.PositiveIntegerField("信頼区間下限", null=True, blank=True)
    upper_bound = models.PositiveIntegerField("信頼区間上限", null=True, blank=True)
    model_version = models.CharField("モデルバージョン", max_length=20, blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "prescription_forecasts"
        verbose_name = "処方予測"
        verbose_name_plural = "処方予測"
        constraints = [
            models.UniqueConstraint(
                fields=["store", "date"],
                name="unique_store_date_forecast",
            )
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.store.name} {self.date}: 予測{self.predicted_count}枚"
