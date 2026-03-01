from django.db import models


# ---------------------------------------------------------------------------
# External data models for prescription forecasting
# ---------------------------------------------------------------------------


class InfluenzaReport(models.Model):
    """IDWR定点報告データ（週次・都道府県別）

    Data source: NIID IDWR速報 CSV
    URL pattern: https://www.niid.go.jp/niid/images/idwr/sokuho/
                 idwr-{YEAR}/{YEAR}{WEEK:02d}/{YEAR}-{WEEK:02d}-teiten.csv
    """

    year = models.PositiveIntegerField("年")
    week = models.PositiveIntegerField("週番号")
    prefecture = models.CharField("都道府県", max_length=10)
    disease = models.CharField("疾病名", max_length=100, default="インフルエンザ")
    patients = models.DecimalField(
        "定点当たり報告数", max_digits=10, decimal_places=2, null=True, blank=True
    )
    total_reports = models.PositiveIntegerField("総報告数", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "influenza_reports"
        verbose_name = "感染症定点報告"
        verbose_name_plural = "感染症定点報告"
        constraints = [
            models.UniqueConstraint(
                fields=["year", "week", "prefecture", "disease"],
                name="unique_influenza_report",
            )
        ]
        ordering = ["-year", "-week"]

    def __str__(self):
        return f"{self.prefecture} {self.year}W{self.week:02d} {self.disease}: {self.patients}"


class WeatherRecord(models.Model):
    """気象庁 過去の気象データ（日次・観測所別）

    Data source: JMA (気象庁) 過去の気象データ・ダウンロード
    URL: https://www.data.jma.go.jp/gmd/risk/obsdl/
    """

    station_name = models.CharField("観測所名", max_length=50)
    station_code = models.CharField("観測所コード", max_length=10, blank=True, default="")
    date = models.DateField("日付")
    avg_temperature = models.DecimalField(
        "日平均気温(℃)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    max_temperature = models.DecimalField(
        "日最高気温(℃)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    min_temperature = models.DecimalField(
        "日最低気温(℃)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    precipitation = models.DecimalField(
        "降水量(mm)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    humidity = models.DecimalField(
        "平均湿度(%)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    snowfall = models.DecimalField(
        "降雪量(cm)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    snow_depth = models.DecimalField(
        "積雪深(cm)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "weather_records"
        verbose_name = "気象データ"
        verbose_name_plural = "気象データ"
        constraints = [
            models.UniqueConstraint(
                fields=["station_name", "date"],
                name="unique_weather_station_date",
            )
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.station_name} {self.date}: {self.avg_temperature}℃"


# Area → nearest JMA station mapping for 62 stores
# Tuple: (station_name, prec_no, block_no)
# block_no 5-digit = 官署 (daily_s1.php), 4-digit = AMeDAS (daily_a1.php)
AREA_STATION_MAP = {
    "旭川":       ("旭川",   "12", "47407"),  # 官署
    "名寄":       ("名寄",   "12", "0008"),   # AMeDAS
    "稚内":       ("稚内",   "11", "47401"),  # 官署
    "留萌":       ("留萌",   "13", "47406"),  # 官署
    "北見・網走": ("北見",   "17", "0074"),   # AMeDAS
    "紋別":       ("紋別",   "17", "47435"),  # 官署
    "富良野":     ("富良野", "12", "0021"),   # AMeDAS (own station)
    "滝川・砂川": ("滝川",   "15", "0041"),   # AMeDAS (own station)
    "帯広":       ("帯広",   "20", "47417"),  # 官署
    "釧路":       ("釧路",   "19", "47418"),  # 官署
    "中標津":     ("中標津", "18", "0086"),   # AMeDAS
}


def is_amedas(block_no: str) -> bool:
    """Return True if the block_no indicates an AMeDAS station (4-digit)."""
    return len(block_no) <= 4


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
