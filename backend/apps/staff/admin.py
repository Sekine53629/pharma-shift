from django.contrib import admin

from .models import Rounder, RounderStoreExperience, Staff


class RounderInline(admin.StackedInline):
    model = Rounder
    extra = 0


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "employment_type", "store", "is_rounder", "is_active")
    list_filter = ("role", "employment_type", "is_rounder", "is_active")
    search_fields = ("name",)
    inlines = [RounderInline]


@admin.register(Rounder)
class RounderAdmin(admin.ModelAdmin):
    list_display = ("staff", "hunter_rank", "can_work_alone", "max_prescriptions")
    list_filter = ("can_work_alone", "has_car", "can_long_distance")


@admin.register(RounderStoreExperience)
class RounderStoreExperienceAdmin(admin.ModelAdmin):
    list_display = ("rounder", "store", "visit_count", "last_visit_date")
