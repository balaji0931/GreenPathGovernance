from django.contrib import admin
from .models import CollectionRecord

@admin.register(CollectionRecord)
class CollectionRecordAdmin(admin.ModelAdmin):
    list_display = ('household', 'outcome', 'is_segregated', 'segregation_rating', 'missed_reason', 'collector', 'village', 'collection_date', 'collection_time')
    list_filter = ('outcome', 'is_segregated', 'segregation_rating', 'village', 'collection_date')
    search_fields = ('household__uid', 'household__head_name', 'household__house_number', 'collector__user__username')
    readonly_fields = ('created_at',)
