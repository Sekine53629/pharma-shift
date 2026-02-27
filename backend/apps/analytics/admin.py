from django.contrib import admin

from .models import PrescriptionForecast, PrescriptionRecord


@admin.register(PrescriptionRecord)
class PrescriptionRecordAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "count", "source")
    list_filter = ("source", "store")


@admin.register(PrescriptionForecast)
class PrescriptionForecastAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "predicted_count", "model_version")
    list_filter = ("store", "model_version")
