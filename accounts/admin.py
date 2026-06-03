from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import StaffUser, OTPCode

@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ['username','get_full_name','role','department','phone','is_active']
    list_filter  = ['role','department','is_active']
    fieldsets    = UserAdmin.fieldsets + (
        ('CareOS Info', {'fields': ('role','phone','department','profile_photo')}),
    )

@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'attempts']
    list_filter = ['created_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'code']
    readonly_fields = ['code', 'created_at', 'expires_at', 'attempts']