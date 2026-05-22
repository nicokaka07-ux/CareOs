from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display    = ['timestamp','user','action','model_name','description']
    list_filter     = ['action','model_name']
    readonly_fields = ['user','action','model_name','object_id','description','ip_address','timestamp']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False