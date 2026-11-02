from django.contrib import admin
from .models import Village, Ward

class WardInline(admin.TabularInline):
    model = Ward
    extra = 1

@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'district', 'state', 'is_active', 'created_at')
    list_filter = ('is_active', 'state', 'district')
    search_fields = ('code', 'name', 'district')
    inlines = [WardInline]

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('ward_number', 'ward_name', 'village', 'is_active')
    list_filter = ('village', 'is_active')
    search_fields = ('ward_number', 'ward_name', 'village__name')
