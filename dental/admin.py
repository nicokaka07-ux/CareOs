from django.contrib import admin
from .models import DentalProcedureCatalog, DentalEncounter

@admin.register(DentalProcedureCatalog)
class DentalProcedureCatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(DentalEncounter)
class DentalEncounterAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'procedure', 'tooth_number', 'created_at')
    search_fields = ('patient__id', 'procedure__name', 'tooth_number')
    list_filter = ('created_at',)