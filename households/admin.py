from django.contrib import admin
from .models import Household

@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ('uid', 'head_name', 'house_number', 'ward', 'village', 'is_active', 'registered_at')
    list_filter = ('village', 'ward', 'is_active')
    search_fields = ('uid', 'head_name', 'house_number', 'phone_number')
    readonly_fields = ('uid', 'qr_code_image', 'registered_at', 'updated_at')
