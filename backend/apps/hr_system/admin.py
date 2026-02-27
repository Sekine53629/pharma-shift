from django.contrib import admin

from .models import HrEvaluation, HrPeriodSummary


@admin.register(HrEvaluation)
class HrEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        "evaluator",
        "rounder",
        "score",
        "evaluation_type",
        "requires_approval",
        "created_at",
    )
    list_filter = ("evaluation_type", "requires_approval")

    def has_change_permission(self, request, obj=None):
        return False  # UPDATE禁止

    def has_delete_permission(self, request, obj=None):
        return False  # DELETE禁止


@admin.register(HrPeriodSummary)
class HrPeriodSummaryAdmin(admin.ModelAdmin):
    list_display = ("rounder", "period_start", "period_end", "computed_hr", "total_points")
    list_filter = ("period_start",)
