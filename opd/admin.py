from django.contrib import admin
from .models import Patient, Appointment, Department, MortalityRecord

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display    = ['patient_id','get_full_name','gender','phone','created_at']
    search_fields   = ['first_name','last_name','patient_id','phone']
    list_filter     = ['gender','blood_group']
    readonly_fields = ['patient_id','created_at']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['queue_number','patient','doctor','department','scheduled_date','status','priority']
    list_filter  = ['status','priority','scheduled_date']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name','is_active']

@admin.register(MortalityRecord)
class MortalityAdmin(admin.ModelAdmin):
    list_display    = ['patient','date_of_death','cause_of_death','attending_doctor']
    readonly_fields = ['created_at']