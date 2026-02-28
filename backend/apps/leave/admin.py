from django.contrib import admin

from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "leave_type", "status", "reviewer", "is_late")
    list_filter = ("leave_type", "status", "is_late")
    search_fields = ("staff__name",)
