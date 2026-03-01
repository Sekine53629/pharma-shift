from django.contrib import admin

from .models import DailyScheduleOverride, StaffingAdjustment, StoreWeeklySchedule


@admin.register(StoreWeeklySchedule)
class StoreWeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "store",
        "day_of_week",
        "is_open",
        "open_time",
        "close_time",
        "staffing_delta",
        "updated_at",
    )
    list_filter = ("day_of_week", "is_open", "store")
    search_fields = ("store__name",)


@admin.register(DailyScheduleOverride)
class DailyScheduleOverrideAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "is_open", "note", "updated_by", "updated_at")
    list_filter = ("is_open", "store")
    search_fields = ("store__name",)
    date_hierarchy = "date"


@admin.register(StaffingAdjustment)
class StaffingAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "delta", "source", "updated_by", "updated_at")
    list_filter = ("source", "shift_period", "store")
    search_fields = ("store__name",)
