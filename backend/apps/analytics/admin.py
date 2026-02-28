from django.contrib import admin

from .models import (
    InfluenzaReport,
    PrescriptionForecast,
    PrescriptionRecord,
    WeatherRecord,
)


@admin.register(PrescriptionRecord)
class PrescriptionRecordAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "count", "source")
    list_filter = ("source", "store")


@admin.register(PrescriptionForecast)
class PrescriptionForecastAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "predicted_count", "model_version")
    list_filter = ("store", "model_version")


@admin.register(InfluenzaReport)
class InfluenzaReportAdmin(admin.ModelAdmin):
    list_display = ("prefecture", "year", "week", "disease", "patients", "total_reports")
    list_filter = ("disease", "year", "prefecture")
    search_fields = ("disease",)


@admin.register(WeatherRecord)
class WeatherRecordAdmin(admin.ModelAdmin):
    list_display = ("station_name", "date", "avg_temperature", "precipitation", "humidity", "snowfall")
    list_filter = ("station_name",)
    date_hierarchy = "date"
