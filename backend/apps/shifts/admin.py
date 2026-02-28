from django.contrib import admin

from .models import Shift, ShiftPeriod


@admin.register(ShiftPeriod)
class ShiftPeriodAdmin(admin.ModelAdmin):
    list_display = ("start_date", "end_date", "request_deadline", "is_finalized")
    list_filter = ("is_finalized",)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "store", "shift_type", "leave_type", "is_confirmed")
    list_filter = ("shift_type", "leave_type", "is_confirmed", "date")
    search_fields = ("staff__name", "store__name")
