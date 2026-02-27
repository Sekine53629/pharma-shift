from django.contrib import admin

from .models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "base_difficulty", "effective_difficulty", "slots", "is_active")
    list_filter = ("area", "is_active")
    search_fields = ("name",)
