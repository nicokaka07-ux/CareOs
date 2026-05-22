from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import StaffUser

@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ['username','get_full_name','role','department','phone','is_active']
    list_filter  = ['role','department','is_active']
    fieldsets    = UserAdmin.fieldsets + (
        ('CareOS Info', {'fields': ('role','phone','department','profile_photo')}),
    )