from django.contrib import admin

from .models import Assignment, SupportSlot


@admin.register(SupportSlot)
class SupportSlotAdmin(admin.ModelAdmin):
    list_display = ("store", "date", "priority", "effective_difficulty_hr", "is_filled")
    list_filter = ("priority", "is_filled", "prescription_forecast")
    search_fields = ("store__name",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("rounder", "slot", "status", "score", "confirmed_by")
    list_filter = ("status",)
